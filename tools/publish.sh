#!/bin/bash
# PUBLISH ONE RUN (the plan's step 3): the private pulse behind Access, the
# public catalog on the explorer's Pages hostname, the catalog's objects to the
# `catalog` R2 bucket by hash.
#
#   tools/publish.sh out/<date>
#
# Needs, from the environment's secrets (never a file in this repository):
#   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID   Pages, R2, Access scope
#   CATALOG_PUBLIC_BASE   the catalog bucket's public URL, ending in /
#   PULSE_HOSTNAME        the pulse's hostname, which an Access app must cover
#
# Exit 3, publishing nothing, when the token is absent: the Cloudflare account
# is the owner's hand action 1, and this step stops rather than works around it.
# It also refuses, before anything is uploaded, when the catalog still points at
# a stub URL, or when no Access application covers the pulse's hostname: the
# pulse is private or it is not published (the plan's step 3 ablation).
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RUN="${1:?usage: tools/publish.sh out/<date>}"
RUN="$(cd "$RUN" && pwd)"
say() { echo "publish: $*"; }
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] || [ -z "${CLOUDFLARE_ACCOUNT_ID:-}" ]; then
  say "no Cloudflare token in this environment (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID) -- nothing published; both sites are in $RUN"
  exit 3
fi
for v in CATALOG_PUBLIC_BASE PULSE_HOSTNAME; do
  [ -n "${!v:-}" ] || { say "REFUSED: $v is not set"; exit 1; }
done
CFG="$ROOT/catalog.json"
BUCKET="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['bucket'])" "$CFG")"
PULSE_PROJECT="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pages']['pulse'])" "$CFG")"
CATALOG_PROJECT="$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['pages']['catalog'])" "$CFG")"
WRANGLER="${WRANGLER:-npx --yes wrangler@3}"
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

# 2. THE CATALOG, rebuilt to point at the bucket, and refused while it points at a stub.
CATALOG_ASSET_BASE="$CATALOG_PUBLIC_BASE" python3 "$ROOT/tools/catalog.py" "$RUN" || { say "REFUSED: the catalog did not build"; exit 1; }
python3 - "$RUN/catalog/objects.json" "$CFG" <<'PY' || { say "REFUSED: the catalog still points at a stub edge URL (agent A's ops/edge/README.md)"; exit 1; }
import json, sys
o, c = json.load(open(sys.argv[1])), json.load(open(sys.argv[2]))
sys.exit(1 if set(c["stub"].values()) & set(o["edge"].values()) else 0)
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

# 5. THE GATE, from outside: the pulse asks for a login.
code="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' "https://$PULSE_HOSTNAME/")"
case "$code" in
  30[0-9]*cloudflareaccess.com*) say "the pulse at https://$PULSE_HOSTNAME/ asks for a login" ;;
  *) say "WARNING: https://$PULSE_HOSTNAME/ answered '$code' without Access in front"; exit 1 ;;
esac
say "published: the pulse (Access) and the catalog ($CATALOG_PROJECT)"
