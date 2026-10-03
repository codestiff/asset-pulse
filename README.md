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
   posts to agent A's intake. Every subject page has a stable URL,
   `/subject/<id>/` (the generator's id, e.g. `/subject/plant/rowan/`; a variant
   the library bakes beside it at `/subject/<id>/<variant>/`), for the game's
   inspect to link to. Under the downloads, here and on the index page only:

   > In the game, tap the build number on the start card seven times to turn on developer mode: inspect any subject and download it from there.

   Objects are named by content hash for the
   `catalog` bucket. Verified locally 2026-10-03 at library 552e8ca.
4. publishing: `tools/publish.sh` -- objects to R2, the pulse to Pages behind
   Access on `pulse.<zone>`, the catalog to the `asset-explorer` Pages project
   on its existing hostname (`asset-explorer.pages.dev`, from the explorer's
   `wrangler.toml`, the only file of the retired app this touches). It reads
   CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID, EDGE_ZONE and
   CATALOG_PUBLIC_BASE from the environment (ITCH_URL optional) and, until
   they are set, stops before deploying with a message naming the missing
   ones (exit 3).
5. the schedule: `.github/workflows/pulse.yml`, the daily run on GitHub
   Actions (cron 05:37 UTC and by hand), deploying the catalog to GitHub Pages
   at `https://codestiff.github.io/asset-pulse/` once it can run; until then a
   daily Routine runs `./daily.sh` in a cloud session.

## The coffee and the priority rule (the-library-as-a-commons step 5)

The catalog's index, and nowhere else, carries a coffee link to GitHub
Sponsors, read from one value (`sponsors_url` in `catalog.json`) and hidden
while it is empty. Beside it, one of two lines:

- while the library's `tools/commission-cost.py` prints "falsifier holds" (a
  coffee pays for a commission): "A sponsor's request is authored first:
  requests from sponsors go to the front of the queue. What is made from them
  is still free for everyone, with its attribution file."
- until then (on 2026-10-03 it printed "$187.75 per held commission, against
  the plan's $100 -- falsifier FIRES"): "A coffee is a thank-you and buys
  nothing: every subject here stays free, and requests are authored in the
  order the library can afford them."

The rule switches by itself on the run after the library's measure changes;
nothing here has to be edited.

## The pulse plan, closed (fable-plans/active/the-pulse-is-a-consumer)

Landed as built, by the owner's decision of 2026-10-03: the public half is a
catalog on GitHub Pages, deployed by a GitHub Actions workflow
(`.github/workflows/pulse.yml`), not R2 behind Access. Its findings:

- **Step 0, the pin and the scorecard:** landed 2026-10-01; the library's own
  `tools/scorecard.py` replaced the prototype on 2026-10-03 and the row reads
  both.
- **Step 1, the renders:** verified on a fresh checkout 2026-10-03 (the
  session hook, the import before the first sheet, 54 subjects, 40 min). The
  failures are the library's, filed in its feedback/: subjects with no ladder,
  close-ups that find no surface at their default height.
- **Step 2, the private page:** one page per subject (scorecard line, band
  sheet, history) and an index with the totals and their trend. Built every
  run; not deployed anywhere (it carries the cost rows and the sheets).
- **Step 3, publishing:** the catalog, public on GitHub Pages: one page per
  subject at `/subject/<id>/`, two numbers from the scorecard, the 1080 bake
  free (CC BY 4.0, ATTRIBUTION.txt and the licence texts in every zip), no
  plate's bytes ever. 14 of 69 entries wait on the library's bake carrying the
  impostor end (filed). The Cloudflare path (`tools/publish.sh`) stays for
  later and stops without its values.
- **Step 4, the schedule:** the workflow runs daily at 05:37 UTC; a cloud
  Routine runs `./daily.sh` until the workflow's first green run.
- **Step 5, the per-band sheet:** in use since 2026-10-02 (the library's
  `tools/rung-sheet.py`).
- **The address:** `https://codestiff.github.io/asset-pulse/` once the two
  steps below are done.

### The owner's two steps, on a phone

1. **Give the workflow a key to the library.**
   - On github.com, tap your picture, then **Settings**, then **Developer
     settings** (at the bottom), then **Personal access tokens**, then
     **Fine-grained tokens**, then **Generate new token**.
   - Name it `asset-pulse library`. Under **Repository access** pick **Only
     select repositories** and choose **asset-generators** and
     **asset-explorer**.
   - Under **Permissions**, **Repository permissions**, set **Contents** to
     **Read-only**. Nothing else.
   - Tap **Generate token** and copy it.
   - Open the **asset-pulse** repository, then **Settings**, **Secrets and
     variables**, **Actions**, **New repository secret**. Name: `LIBRARY_TOKEN`.
     Paste the token. **Add secret**.
2. **Turn on the public page.**
   - In the **asset-pulse** repository: **Settings**, then **Pages**.
   - Under **Build and deployment**, set **Source** to **GitHub Actions**.
   - (The repository is private: GitHub serves Pages from a private
     repository only on a paid plan. If the Source menu is missing, that is
     why.)

Then, in the repository's **Actions** tab, open **pulse** and tap **Run
workflow**, or wait for 05:37 UTC. The run takes about an hour; the address
above then shows the catalog.

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

- 2026-10-03, going public (the owner: "If we don't have a license issue, sure,
  go public"): there is none -- the baked assets are CC BY 4.0 (`assets_licence`
  in ops/runtime/runtime.toml), each download carries ATTRIBUTION.txt and the
  studio's LICENSE-PLATES.md, LICENSE-RUNTIME.md and PLATES-CC-BY-4.0.txt, and
  the owner's reserved plates never ship as bytes (the catalog refuses to write
  any file whose sha256 is a plate's).
- The catalog goes to GitHub Pages as a workflow artifact, not as committed
  files: CLAUDE.md keeps images and geometry out of git, and an artifact serves
  the same site. Only history.csv and the pin are committed by the workflow.
- The workflow needs the LIBRARY_TOKEN secret (read on the private library and
  explorer) and Pages on with "GitHub Actions" as its source; run #1
  (2026-10-03, by hand) stopped at the token with its message. The cloud
  Routine stays on until the workflow's first green run, so no day goes
  without a row; then the Routine is disabled.
- The Pages URL is recorded here, not in the library's pulse plan: this
  repository never edits the library.
- 2026-10-03, the subject URL pattern `/subject/<id>/` (variants
  `/subject/<id>/<variant>/`) is recorded here for the game's inspect, not in
  the library's pulse plan, which this repository never edits.
- 2026-10-03, the commons' step 5: built, with the priority line gated on the
  library's own measure (`tools/commission-cost.py`), because the plan says
  step 5 waits while that measure fires and the dispatch asked for it now.
  The link is empty, so nothing shows yet.

## Licence

The catalog and the plates are CC BY 4.0, the code MIT: see LICENSE.md.
- 2026-10-03 23:57 UTC, workflow run #4 green (70 min, library bdc29a71, 90 subjects, 70 downloads): the cloud Routine "asset-pulse daily run" is disabled; the workflow is the daily run from here.
