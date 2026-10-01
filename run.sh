#!/bin/bash
# THE PULSE, ONE RUN: sync the library to its pin, print the scorecard, append
# the day's totals to history.csv, and (step 1) render every subject's bands.
#
#   ./run.sh                 one run, into out/<date>/
#   ./run.sh --bump          first move the pin to the library's main
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
echo "run: renders are step 1 of the plan (not yet)"
