"""tools/commit_code.py — stage, commit, and push CODE changes in one call.

The code-side counterpart of ``commit_push_data.py``.  This desktop client only
honours permission rules it writes itself (via "Always allow"), and it keys
them to the **exact command string** — so a command that varies its arguments
(paths, message) re-prompts every time.  The fix is a **fixed invocation**:

    .venv\\Scripts\\python.exe tools/commit_code.py

with NO arguments reads the commit spec from ``tools/scratch/commit.json``
(gitignored).  Write that file first (message + paths), then run the fixed
command — one "Always allow" covers it forever.

``tools/scratch/commit.json``::

    {
      "message_file": "tools/scratch/msg.txt",   // or "message": "subject line"
      "paths": ["damage.py", "tests/test_damage_core.py"],
      "no_push": false
    }

The explicit ``-F/-m paths...`` form still works for one-offs.

Safety rails, on purpose:
* **Explicit paths only** — no blanket ``-A`` staging; you say what ships.
* Add + commit + push only — never reset/checkout/rebase; those stay manual.
* Refuses an empty commit (nothing staged from the given paths).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = os.path.join(ROOT, "tools", "scratch", "commit.json")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def _resolve(spec_file: str, message: str | None, message_file: str | None,
             paths: list[str], no_push: bool):
    """Return (message, message_file, paths, no_push), reading the fixed spec
    file when no explicit args were supplied."""
    if paths:
        return message, message_file, paths, no_push
    if not os.path.exists(spec_file):
        raise SystemExit(f"no paths given and no spec at {spec_file} — "
                         "write the commit spec first (message + paths)")
    with open(spec_file, encoding="utf-8") as f:
        spec = json.load(f)
    p = spec.get("paths") or []
    if not p:
        raise SystemExit(f"{spec_file}: 'paths' is empty")
    return (spec.get("message"), spec.get("message_file"), p,
            bool(spec.get("no_push", False)))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Stage + commit + push code changes.")
    ap.add_argument("paths", nargs="*", help="files/dirs to stage (explicit "
                    "one-off form; omit to read tools/scratch/commit.json)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("-F", "--file", help="commit-message file")
    g.add_argument("-m", "--message", help="inline commit message")
    ap.add_argument("--no-push", action="store_true", help="commit only")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    message, message_file, paths, no_push = _resolve(
        _SPEC, args.message, args.file, args.paths, args.no_push)
    if not (message or message_file):
        raise SystemExit("no commit message (need 'message' or 'message_file')")

    r = _git("add", "--", *paths)
    if r.returncode != 0:
        raise SystemExit(f"git add failed:\n{r.stderr.strip()}")

    staged = _git("diff", "--cached", "--name-only").stdout.strip()
    if not staged:
        raise SystemExit("nothing staged from the given paths — refusing an empty commit")

    # Commit ONLY the named paths — pathspec-limited so anything the user (or
    # an earlier step) happens to have staged never rides along uninvited.
    if message_file:
        path = message_file if os.path.isabs(message_file) else os.path.join(ROOT, message_file)
        r = _git("commit", "-q", "-F", path, "--", *paths)
    else:
        r = _git("commit", "-q", "-m", message, "--", *paths)
    if r.returncode != 0:
        raise SystemExit(f"git commit failed:\n{r.stderr.strip()}\n{r.stdout.strip()}")

    sha = _git("rev-parse", "--short", "HEAD").stdout.strip()
    subject = _git("log", "-1", "--format=%s").stdout.strip()
    if no_push:
        print(f"Committed {sha}: {subject} ({len(staged.splitlines())} file(s), not pushed)")
        return
    r = _git("push")
    if r.returncode != 0:
        raise SystemExit(f"committed {sha} but push failed:\n{r.stderr.strip()}")
    print(f"Committed + pushed {sha}: {subject} ({len(staged.splitlines())} file(s))")


if __name__ == "__main__":
    main()
