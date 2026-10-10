#!/usr/bin/env python3
"""THE PUBLIC CATALOG NEVER SHRINKS BY ACCIDENT (row 215, option A, the owner
2026-10-10): a run's catalog is deployed only when it lists at least as many
subjects as the one live now. A run cut short by the registry bake's budget
(the glTF surface bake, asset-generators 49cf1557) ships a catalog of what
finished; this keeps the fuller live one instead.

    tools/catalog_guard.py <new catalog dir> <live catalog URL or dir>

Exit 0: deploy (prints both counts). Exit 1: keep the live one. No live page
(404: the first deploy, Pages just turned on) counts as zero, so the first
catalog always deploys; a live page that cannot be read for any other reason
(the network, a 5xx) keeps it, since a fuller catalog may be behind the error. A subject is one card on the index
(`<div class=card>`, tools/catalog.py), counted the same way on both sides.
"""
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

CARD = re.compile(r"<div class=card>")


def count(html):
    return len(CARD.findall(html or ""))


def read(where):
    if not where.startswith(("http://", "https://")):
        f = Path(where) / "index.html"
        return f.read_text(encoding="utf-8") if f.exists() else ""
    try:
        with urllib.request.urlopen(where.rstrip("/") + "/", timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("catalog-guard: no live catalog (404); counting it as 0")
            return ""
        raise SystemExit("catalog-guard: KEEP the live catalog -- it could not be read (HTTP %d)" % e.code)
    except Exception as e:  # noqa: BLE001
        raise SystemExit("catalog-guard: KEEP the live catalog -- it could not be read (%s)" % e)


def main(argv):
    if len(argv) != 3:
        sys.exit(__doc__)
    new, live = count(read(str(argv[1]))), count(read(str(argv[2])))
    if new >= live:
        print("catalog-guard: deploy -- %d subject(s) now, %d live" % (new, live))
        return 0
    print("catalog-guard: KEEP the live catalog -- this run has %d subject(s), the live one %d" % (new, live))
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
