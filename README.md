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

    ./daily.sh                        THE DAILY RUN: everything below, then commit,
                                      push and print a report -- what a session runs

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

## Steps (the plan's, and the release plan's agent D)

0. the pin, the sync, the scorecard, the first history row -- done
1. the renders: the library's per-band sheet and close-up for every subject --
   verified by one full run 2026-10-02 (pin 93fed38, 37 min, 54 subjects; 17
   fail in the library's tools, filed in its feedback/)
2. the page: one per subject (scorecard row, band sheet, history) and an index
   with the totals and their trend -- `tools/site.py`, checked at 390 px
3. the catalog, the pulse's public half: `tools/bake.sh` (asset-explorer's
   bake, pinned in `explorer.lock`, run as its refresh.sh ran it), then
   `tools/catalog.py`: one static page per subject from the library's committed
   JSON (class, size, rungs, ladder end, taxon, use), its close-ups and a
   `<model-viewer>` of rung 0; two numbers from the scorecard (draw cost at the
   1080 baseline, error at the finest affordable band); the 1080 bake free as
   a zip of every rung's glTF, the impostor and its atlas when the ladder ends
   in one, `ATTRIBUTION.txt` (the card's plates, contributor and licence, in
   the library's own form) and the runtime's open LICENSE. A subject whose
   ladder ends in an impostor is offered only when its bake carries the
   impostor: the ladder end is part of the asset (the owner, 2026-10-03).
   Finer builds will be pay-what-you-want on itch, the only store, from stage 1
   (`ITCH_URL`); until then the pages read "free at 1080; finer builds soon"
   and the free 1080 download is the whole offer. The request form
   posts to agent A's intake. Objects are named by content hash for the
   `catalog` bucket. Verified locally 2026-10-03 at library 552e8ca.
4. publishing: `tools/publish.sh` -- objects to R2, the pulse to Pages behind
   Access on `pulse.<zone>`, the catalog to the `asset-explorer` Pages project
   on its existing hostname (`asset-explorer.pages.dev`, from the explorer's
   `wrangler.toml`, the only file of the retired app this touches). It reads
   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, EDGE_ZONE and
   CATALOG_PUBLIC_BASE from the environment (ITCH_URL optional) and, until
   they are set, stops before deploying with a message naming the missing
   ones (exit 3).
5. the schedule: a daily Routine running `./daily.sh`

## Calls made here (the plan lives in the library, which this repository never edits)

- 2026-10-03, the owner's five decisions (relayed by Fable) applied in f63acca.
- A subject whose committed ladder ends in an impostor has no download until
  the bake carries the impostor rung and its atlas, rather than a download
  without its end (decision 1). Filed: `the-bake-stops-at-the-last-mesh-rung-4bdef5cf`.
- "Error at the finest affordable band" is the scorecard's `error_px` on the
  lowest-numbered band it marks `covered`; "cost at the 1080 baseline" is its
  `src_cost`. A variant shows its generator's default numbers and says so.
- Plate licences are printed as the manifest's `licence` field holds them; all
  123 still read "all rights reserved". Filed:
  `every-plates-licence-still-reads-all-rights-reserved-94e1e0e6`.
- The download's own licence is the runtime's (`ops/runtime/runtime.toml`,
  MIT), shipped as LICENSE beside ATTRIBUTION.txt.
- The band sheets are private (decision 2: two numbers only on public pages).
- The baked-channel bake falls back to the library's default when it refuses
  (filed: `three-flat-baked-channels-refuse-the-whole-transfer-bake-b6c7043d`).
- 2026-10-03, the plan's revision (itch is the only store, from stage 1):
  ITCH_URL is optional; empty, the paid-build link reads "free at 1080;
  finer builds soon", and publish no longer waits on it.
