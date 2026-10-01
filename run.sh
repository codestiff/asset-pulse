#!/bin/bash
# THE PULSE, ONE RUN: sync the library to its pin, print the scorecard, append
# the day's totals to history.csv, render every subject's bands (step 1, with
# the library's per-band sheet, step 5) and write the page (step 2, out/<date>/site/).
#
#   ./run.sh                 one run, into out/<date>/
#   ./run.sh --bump          first move the pin to the library's main
#   ./run.sh --no-render     the scorecard and the row only
#   PULSE_CAP_S=1800         the per-subject time cap for the renders
#   PULSE_BAND_CAP_S=300     the cap on one band's derivation search (the sheet's own)
#   PULSE_DERIVE=none        drawn today only: no search, no derived column (fast)
#   PULSE_ONLY="a/b c/d"     render only these subjects (a manual look)
#
# Rules (fable-plans/active/the-pulse-is-a-consumer, in the library):
#   - every number comes from the library's scorecard tool, every frame from the
#     library's sheet and close-up tools; this script decides nothing about
#     scoring or rendering;
#   - nothing generated is committed but history.csv, one dated row per run;
#   - a failed run writes a row that says so, never nothing.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
DATE="$(date -u +%Y-%m-%d)"
OUT="$ROOT/out/$DATE"
mkdir -p "$OUT"
HIST="$ROOT/history.csv"
[ -f "$HIST" ] || echo "date,pin,status,subjects,bands,covered_hand,covered_library,uncovered,fully_covered,fully_from_rung0,sources_over_ceiling" > "$HIST"
fail_row() {
  PIN="$(sed -n 's/^commit=//p' library.lock)"
  echo "$DATE,$PIN,failed:$1,,,,,,,," >> "$HIST"
  echo "run: FAILED ($1); a row says so in history.csv" >&2
  exit 1
}
if [ "${1:-}" = "--bump" ]; then
  tools/sync-library.sh --bump main || fail_row "bump"
fi
tools/sync-library.sh || fail_row "sync"
tools/sync-library.sh --verify || fail_row "verify"
PIN="$(sed -n 's/^commit=//p' library.lock)"
# THE SCORECARD: the library's tool when it exists (the tooling plan's step 10),
# the prototype beside the library's plans until then. Run from the library root,
# since both read the library's committed JSON by relative path.
SCORECARD="library/tools/scorecard.py"
[ -f "$SCORECARD" ] || SCORECARD="library/fable-plans/notes/scorecard-prototype.py"
( cd library && python3 "../$SCORECARD" ) > "$OUT/scorecard.txt" || fail_row "scorecard"
TOTALS="$( cd library && python3 "../$SCORECARD" --json )" || fail_row "scorecard-json"
ROW="$(python3 - "$DATE" "$PIN" "$TOTALS" <<'PY'
import json, sys
d, pin, t = sys.argv[1], sys.argv[2], json.loads(sys.argv[3])
print(",".join(str(x) for x in [d, pin, "ok", t["subjects"], t["bands"], t["covered_hand"],
      t["covered_derived"], t["uncovered"], t["fully"], t["fully_rung0_only"], t["src_over"]]))
PY
)" || fail_row "row"
# One row per date: a re-run on the same day replaces the day's row.
grep -v "^$DATE," "$HIST" > "$HIST.tmp" && mv "$HIST.tmp" "$HIST"
echo "$ROW" >> "$HIST"
echo "run: scorecard in $OUT/scorecard.txt; history row: $ROW"
# STEP 1, THE RENDERS: the library's own sheet and close-up for every subject
# that has a card, each under a per-subject time cap, into out/<date>/<id>/.
# The library decides every frame (tools/rung-sheet.py, tools/closeup.sh); this
# loop only names the subject and the directory. A subject that fails gets a
# manifest row that says so, and the run goes on. `--no-render` skips it.
if [ "${PULSE_RENDER:-1}" = "1" ] && [ "${1:-}" != "--no-render" ] && [ "${2:-}" != "--no-render" ]; then
  command -v godot >/dev/null 2>&1 || fail_row "godot-missing"
  command -v xvfb-run >/dev/null 2>&1 || fail_row "xvfb-missing"
  # A fresh checkout has no class cache; the import builds it (seconds) and is
  # a no-op when it exists for this pin.
  if [ ! -f library/.godot/global_script_class_cache.cfg ] || [ "$(cat library/.godot/pulse-pin 2>/dev/null)" != "$PIN" ]; then
    ( cd library && godot --headless --path . --import >/dev/null 2>&1 ) || fail_row "import"
    echo "$PIN" > library/.godot/pulse-pin
  fi
  CAP="${PULSE_CAP_S:-1800}"
  # THE PER-BAND SHEET (the plan's step 5, the library's plans/049 step 3): each
  # band drawn today beside the rung derived from rung 0, and its numbers as
  # sheet-bands.json for the page. The search is the slow part, capped per band
  # by the sheet itself; PULSE_DERIVE=none leaves it out.
  SHEET_ARGS=(--derive-cap "${PULSE_BAND_CAP_S:-300}")
  [ "${PULSE_DERIVE:-}" = "none" ] && SHEET_ARGS=(--derive none)
  MANIFEST="$OUT/manifest.json"
  echo "[" > "$MANIFEST"; first=1; n=0; failed=0; t0=$(date +%s)
  for card in library/generators/*/*.card.json; do
    id="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['id'])" "$card" 2>/dev/null)" || continue
    [ -n "$id" ] || continue
    if [ -n "${PULSE_ONLY:-}" ] && [[ " $PULSE_ONLY " != *" $id "* ]]; then continue; fi
    dir="$OUT/${id//\//_}"; mkdir -p "$dir"
    s=$(date +%s); status="ok"
    ( cd library && timeout "$CAP" python3 tools/rung-sheet.py "$id" --out "$dir/sheet.jpg" "${SHEET_ARGS[@]}" ) > "$dir/sheet.log" 2>&1 || status="sheet-failed"
    if [ "$status" = "ok" ]; then
      ( cd library && SHOT_DIR="$dir" timeout "$CAP" tools/closeup.sh "$id" ) > "$dir/closeup.log" 2>&1 || status="closeup-failed"
    fi
    secs=$(( $(date +%s) - s )); n=$((n+1)); [ "$status" = "ok" ] || failed=$((failed+1))
    images="$(cd "$dir" && ls *.jpg *.png 2>/dev/null | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().split()))")"
    [ $first = 1 ] || echo "," >> "$MANIFEST"; first=0
    printf '  {"id": "%s", "status": "%s", "seconds": %d, "images": %s}' "$id" "$status" "$secs" "$images" >> "$MANIFEST"
    echo "render $id: $status in ${secs}s"
  done
  echo "" >> "$MANIFEST"; echo "]" >> "$MANIFEST"
  echo "run: rendered $n subjects, $failed failed, in $(( $(date +%s) - t0 )) s; manifest $MANIFEST"
  # STEP 2, THE PAGE: static HTML from this run's output and the history.
  python3 tools/site.py "$OUT" || fail_row "site"
else
  echo "run: renders skipped (--no-render)"
fi
