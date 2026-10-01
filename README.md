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

    ./run.sh            # sync to the pin, print the scorecard, append today's row
    ./run.sh --bump     # first move the pin to the library's main

Output lands in `out/<date>/` (gitignored). `history.csv` is the only generated
file committed: one row per run, the day's totals, and `failed:<step>` when a
run did not finish.

## Rules

- The library is never edited from here. A gap goes to the library's
  `feedback/`.
- No images and no generated geometry in git, here or in the library. Images
  go to the object store (step 3).
- The pulse reports; it is not a gate on anything.
- The page is private: the owner's login only (step 3). The public face of the
  library is `asset-explorer`, which hands people assets without the code.

## Steps (the plan's)

0. the pin, the sync, the scorecard, the first history row -- this
1. the renders: the library's per-band sheet and close-up for every subject
2. the page: one per subject plus an index with the totals and their trend
3. publishing: images to R2, the site to Pages, Access in front of both
4. the schedule: a daily Routine, then the nightly runner's cron
5. the per-band sheet, when the library lands it
