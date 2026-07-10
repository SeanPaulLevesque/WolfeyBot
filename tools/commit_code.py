"""tools/commit_code.py — stage, commit, and push CODE changes in one call.

The code-side counterpart of ``commit_push_data.py``, closing the last gap
that forced multi-command git chains (which fight the permission matcher).
One allowlisted invocation replaces add + commit + push:

    .venv\\Scripts\\python.exe tools/commit_code.py -F <msgfile> path [path ...]
    .venv\\Scripts\\python.exe tools/commit_code.py -m "short subject" path [path ...]

Safety rails, on purpose:
* **Explicit paths only** — no blanket ``-A`` staging; you say what ships.
* Message from a file (``-F``, written with the Write tool) or a short ``-m``.
* Add + commit + push only — never reset/checkout/rebase; those stay manual.
* Refuses an empty commit (nothing staged from the given paths).
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Stage + commit + push code changes.")
    ap.add_argument("paths", nargs="+", help="files/dirs to stage (explicit only)")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("-F", "--file", help="commit-message file")
    g.add_argument("-m", "--message", help="inline commit message")
    ap.add_argument("--no-push", action="store_true", help="commit only")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    r = _git("add", "--", *args.paths)
    if r.returncode != 0:
        raise SystemExit(f"git add failed:\n{r.stderr.strip()}")

    staged = _git("diff", "--cached", "--name-only").stdout.strip()
    if not staged:
        raise SystemExit("nothing staged from the given paths — refusing an empty commit")

    # Commit ONLY the named paths — pathspec-limited so anything the user (or
    # an earlier step) happens to have staged never rides along uninvited.
    if args.file:
        path = args.file if os.path.isabs(args.file) else os.path.join(ROOT, args.file)
        r = _git("commit", "-q", "-F", path, "--", *args.paths)
    else:
        r = _git("commit", "-q", "-m", args.message, "--", *args.paths)
    if r.returncode != 0:
        raise SystemExit(f"git commit failed:\n{r.stderr.strip()}\n{r.stdout.strip()}")

    sha = _git("rev-parse", "--short", "HEAD").stdout.strip()
    subject = _git("log", "-1", "--format=%s").stdout.strip()
    if args.no_push:
        print(f"Committed {sha}: {subject} ({len(staged.splitlines())} file(s), not pushed)")
        return
    r = _git("push")
    if r.returncode != 0:
        raise SystemExit(f"committed {sha} but push failed:\n{r.stderr.strip()}")
    print(f"Committed + pushed {sha}: {subject} ({len(staged.splitlines())} file(s))")


if __name__ == "__main__":
    main()
