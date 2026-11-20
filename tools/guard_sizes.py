#!/usr/bin/env python3
"""Pre-push file-size guard for the data pipelines.

Why (session 7085e643, 2026-11-20): `Refresh Kalshi demo data` failed on every run from
14:10 UTC onward because a freshly collected `data/snapshot.json` was 111.97 MB and
GitHub's pre-receive hook declines a push containing any file over 100 MB:

    remote: error: File data/snapshot.json is 111.97 MB; this exceeds GitHub's file size limit
    remote: pre-receive hook declined

Six push attempts were made before the job said anything, and each attempt re-sent the
same doomed pack. This script moves the check to BEFORE the commit, so a size problem
fails in one second with the file named, instead of six rejected pushes.

Usage:  python3 tools/guard_sizes.py [--max-mb 95] [dir ...]     (default dir: data)

Exit codes: 0 = every file is under the limit, 1 = at least one file is over.
Warning threshold is the 50 MB per-file size GitHub recommends (it does not block).
Sources: https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GITHUB_HARD_LIMIT_MB = 100  # push is declined above this
GITHUB_RECOMMENDED_MB = 50  # warning only


def shown(p: Path) -> str:
    try:
        return str(p.relative_to(ROOT))
    except ValueError:      # scanning a directory outside the repo (tests, CI temp dirs)
        return str(p)


def scan(dirs: list[str], max_mb: float) -> tuple[list[str], list[str], int, int]:
    over, warn, files, total = [], [], 0, 0
    for d in dirs:
        base = Path(d)
        if not base.is_absolute():
            base = ROOT / base
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file():
                continue
            size = p.stat().st_size
            files += 1
            total += size
            mb = size / 1e6
            if mb > max_mb:
                over.append(f"{shown(p)} is {mb:.2f} MB (guard limit {max_mb} MB)")
            elif mb > GITHUB_RECOMMENDED_MB:
                warn.append(f"{shown(p)} is {mb:.2f} MB, over GitHub's "
                            f"recommended {GITHUB_RECOMMENDED_MB} MB (push still allowed)")
            elif mb > 25:
                warn.append(f"{shown(p)} is {mb:.2f} MB — large for a browser payload")
    return over, warn, files, total


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="*", default=["data"])
    ap.add_argument("--max-mb", type=float, default=95.0,
                    help=f"fail above this per-file size (default 95 MB, GitHub hard limit "
                         f"{GITHUB_HARD_LIMIT_MB} MB)")
    args = ap.parse_args()

    over, warn, files, total = scan(args.dirs, args.max_mb)
    print(f"guard: {files} files, {total / 1e6:.2f} MB total, per-file limit {args.max_mb} MB")
    for w in warn:
        print(f"::warning::{w}")
        print(f"WARN  {w}")
    if over:
        for o in over:
            print(f"::error::{o} — refusing to commit; raise the publish cap "
                  f"(KALSHI_PUB_MAX_ROWS_PER_TOPIC) or shrink the payload before pushing")
            print(f"FAIL  {o}")
        return 1
    print("guard OK — every file is under the push limit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
