#!/bin/bash
# PUBLISH ONE RUN (the plan's step 3): the private pulse behind Access, the
# public catalog on the explorer's Pages hostname, the catalog's objects to the
# `catalog` R2 bucket by hash.
#
#   tools/publish.sh out/<date>
#
# Needs, from the environment's secrets (never a file in this repository):
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID   Pages, R2, Access scope
#   EDGE_ZONE             the owner's domain: the intake's URL and both hostnames
#   CATALOG_PUBLIC_BASE   the catalog bucket's public URL, ending in /
# The pulse's hostname is pulse.<zone> (ops/edge/README.md, behind Access); the
# catalog's is read from the explorer's Pages config (explorer/wrangler.toml).
#
# Exit 3, publishing nothing, when the token is absent: the Cloudflare account
# is the owner's hand action 1, and this step stops rather than works around it.
# It also refuses, before anything is uploaded, when no Access application
# covers the pulse's hostname (the pulse is private or it is not published: the
# plan's step 3 ablation), or when the catalog's request form points at a local
# URL. An empty itch_url in catalog.json is a warning: the subject pages say the
# paid builds' page is not up yet.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="${1:?usage: tools/publish.sh out/<date>}"
RUN="$(cd "$RUN" && pwd)"
say() { echo "publish: $*"; }
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  say "no Cloudflare token in this environment (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID) -- nothing published; both sites are in $RUN"
  exit 3
fi
for v in EDGE_ZONE CATALOG_PUBLIC_BASE; do
  [ -n "${!v:-}" ] || { say "REFUSED: $v is not set"; exit 1; }
done
CFG="$ROOT/catalog.json"
BUCKET="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['bucket'])" "$CFG")"
PULSE_PROJECT="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pages']['pulse'])" "$CFG")"
CATALOG_PROJECT="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pages']['catalog'])" "$CFG")"
WRANGLER="${WRANGLER:-npx --yes wrangler@3}"
PULSE_HOSTNAME="pulse.$EDGE_ZONE"
CATALOG_HOSTNAME="$(sed -n 's/^# hostname: //p' "$ROOT/explorer/wrangler.toml" 2>/dev/null | sed "s/<zone>/$EDGE_ZONE/")"
[ -n "$CATALOG_HOSTNAME" ] || { say "REFUSED: no '# hostname:' in explorer/wrangler.toml (run tools/bake.sh to check out the explorer pin)"; exit 1; }
[ -n "$(python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('itch_url',''))" "$CFG")" ] \
  || say "warning: itch_url is empty in catalog.json; the pages say the pay-what-you-want page is not up yet"
API="https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID"
auth=(-H "Authorization: Bearer $CLOUDFLARE_API_TOKEN")

# 1. THE PULSE IS PRIVATE OR IT IS NOT PUBLISHED.
apps="$(curl -fsS "${auth[@]}" "$API/access/apps?per_page=100")" || { say "REFUSED: cannot read the Access applications"; exit 1; }
python3 - "$PULSE_HOSTNAME" "$apps" <<'PY' || { say "REFUSED: no Access application covers $PULSE_HOSTNAME -- the pulse would be public"; exit 1; }
import json, sys
host, apps = sys.argv[1], json.loads(sys.argv[2]).get("result", [])
doms = [d for a in apps for d in ([a.get("domain", "")] + [s.get("uri", "") for s in a.get("destinations", []) or []])]
sys.exit(0 if any(d.split("/")[0] in (host, "*." + host.split(".", 1)[-1]) for d in doms) else 1)
PY

# 2. THE CATALOG, rebuilt to point at the bucket and the public intake.
CATALOG_ASSET_BASE="$CATALOG_PUBLIC_BASE" python3 "$ROOT/tools/catalog.py" "$RUN" || { say "REFUSED: the catalog did not build"; exit 1; }
python3 - "$RUN/catalog/objects.json" <<'PY' || { say "REFUSED: the catalog's request form points at a local URL"; exit 1; }
import json, sys
u = json.load(open(sys.argv[1]))["edge"].get("intake", "")
sys.exit(1 if "127.0.0.1" in u or "localhost" in u else 0)
PY

# 3. THE OBJECTS, by hash: a name is its content, so a put is idempotent.
n=0
for f in "$RUN"/catalog/objects/*; do
  $WRANGLER r2 object put "$BUCKET/$(basename "$f")" --file "$f" --remote >/dev/null || { say "upload failed: $(basename "$f")"; exit 1; }
  n=$((n+1))
done
say "$n object(s) in the $BUCKET bucket"

# 4. THE TWO SITES. The catalog's pages only (its objects are in the bucket).
STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
( cd "$RUN/catalog" && tar --exclude=./objects --exclude=./objects.json -cf - . ) | ( cd "$STAGE" && tar -xf - )
$WRANGLER pages deploy "$STAGE" --project-name "$CATALOG_PROJECT" --branch main --commit-dirty=true || { say "the catalog deploy failed"; exit 1; }
$WRANGLER pages deploy "$RUN/site" --project-name "$PULSE_PROJECT" --branch main --commit-dirty=true || { say "the pulse deploy failed"; exit 1; }
# The hostnames on their projects (idempotent: an existing domain answers 409).
for pair in "$CATALOG_PROJECT=$CATALOG_HOSTNAME" "$PULSE_PROJECT=$PULSE_HOSTNAME"; do
  proj="${pair%%=*}"; host="${pair#*=}"
  code="$(curl -s -o /dev/null -w '%{http_code}' "${auth[@]}" -H 'Content-Type: application/json' \
    -X POST "$API/pages/projects/$proj/domains" --data "{\"name\":\"$host\"}")"
  case "$code" in 200|409) say "$host -> $proj" ;; *) say "could not point $host at $proj (HTTP $code)"; exit 1 ;; esac
done

# 5. THE GATE, from outside: the pulse asks for a login.
code="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "https://$PULSE_HOSTNAME/")"
case "$code" in
  30[0-9]*cloudflareaccess.com*) say "the pulse at https://$PULSE_HOSTNAME/ asks for a login" ;;
  *) say "WARNING: https://$PULSE_HOSTNAME/ answered '$code' without Access in front"; exit 1 ;;
esac
say "published: the pulse at https://$PULSE_HOSTNAME/ (Access) and the catalog at https://$CATALOG_HOSTNAME/"
