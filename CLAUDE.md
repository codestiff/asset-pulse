# asset-pulse -- working here

A consumer of `codestiff/asset-generators`, pinned in `library.lock`. Read
`README.md`; the plan is the library's `fable-plans/active/the-pulse-is-a-consumer`.

- Start of every session: `tools/sync-library.sh --bump main && ./run.sh`.
- The library under `library/` is never edited. A gap goes to the library's
  `feedback/`.
- Every number comes from the library's scorecard tool, every frame from its
  sheet and close-up tools. This repository decides nothing about scoring or
  rendering; if it needs to, that is a feedback entry, not code here.
- Commit only `history.csv` from a run. No images, no geometry, no library files.
