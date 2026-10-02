# asset-pulse

The owner's daily read of the asset library: every generator, its scorecard
row, and (step 1) its bands rendered, on one private page, with a history so
the page shows a direction and not a snapshot.

This repository is a CONSUMER of `codestiff/asset-generators`, pinned by commit
in `library.lock`, exactly as `transect` is. It calls the library's tools and
decides nothing itself about scoring or rendering, so it cannot drift from the
library: a change there moves the pulse at the next bump and nowhere else. The
plan it executes is the library's
`fable-plans/active/the-pulse-is-a-consumer`.

## Run

    ./run.sh                          sync to the pin, scorecard, history row, renders, page
    ./run.sh --bump                   first move the pin to the library's main
    ./run.sh --no-render              the scorecard and the row only
    PULSE_BACKLOG=0 ./run.sh          skip the derivation backlog (a quick look)
    PULSE_DERIVE=none ./run.sh        drawn today only: no derived column
    PULSE_ONLY="built/vase" ./run.sh  render one subject, for a manual look

Output lands in `out/<date>/` (gitignored): `scorecard.txt`, `manifest.json`,
one directory per subject (the library's sheet pages, `sheet-bands.json`, the
close-up) and `site/` -- `index.html` and one page per subject, static, images
under 100 KB. `history.csv` is the only generated file committed: one row per
run, the day's totals, and `failed:<step>` when a run did not finish.

The derivation search is the slow part and runs once, in the backlog step
(hours on a full backlog, little on a quiet day); the sheets then read its
goal table and take seconds each. Each subject's renders are capped by the run
(`PULSE_CAP_S`, 1800).

## Rules

- The library is never edited from here, with one exception: the derivation
  backlog (`tools/backlog.sh`). The pulse runs the library's own expensive
  job once a day (the owner, 2026-10-02: pay for it once) and pushes exactly
  the files that job writes -- the derivation tables and records -- through the
  library's gate, or to `run/derive-backlog-<date>` when the gate refuses. A
  gap goes to the library's `feedback/`.
- No images and no generated geometry in git, here or in the library. Images
  go to the object store (step 3).
- The pulse reports; it is not a gate on anything.
- The page is private: the owner's login only (step 3). The public face of the
  library is `asset-explorer`, which hands people assets without the code.

## Steps (the plan's)

0. the pin, the sync, the scorecard, the first history row -- done
1. the renders: the library's per-band sheet and close-up for every subject --
   written; not yet verified by one full run
2. the page: one per subject plus an index with the totals and their trend --
   `tools/site.py`, checked on one subject at phone width; not yet on a full run
3. publishing: images to R2, the site to Pages, Access in front of both --
   not started: needs the owner's Cloudflare account and an Access policy
4. the schedule: a daily Routine, then the nightly runner's cron -- not started
5. the per-band sheet -- landed in the library (`plans/049` step 3, pinned at
   6fdc79f); `run.sh` calls it and the page reads its `sheet-bands.json`
