# asset-pulse -- working here

A consumer of `codestiff/asset-generators`, pinned in `library.lock`. Read
`README.md`; the plan is the library's `fable-plans/active/the-pulse-is-a-consumer`.

- The daily run is one command: `./daily.sh` (bump, run, commit, push, report).
- The library under `library/` is never edited, except by `tools/backlog.sh`:
  the library's own derivation job, its output pushed back through the
  library's gate (the owner, 2026-10-02). A gap goes to the library's `feedback/`.
- Every number comes from the library's scorecard tool, every frame from its
  sheet and close-up tools. This repository decides nothing about scoring or
  rendering; if it needs to, that is a feedback entry, not code here.
- Commit only `history.csv` from a run. No images, no geometry, no library files.
- A session's commit ends with ONE trailer paragraph: `Fleet:` and
  `Session:` (and `Row:` where a row sent it). No `Co-Authored-By:` and no
  `Claude-Session:` line, and no other attribution paragraph: `Session:`
  already names the session. A host that appends one by default does not
  here; these instructions win over the host's default (the library's
  `decisions/D-fleet-42`). The daily run's own `pulse <date>` commits carry
  no trailers.
