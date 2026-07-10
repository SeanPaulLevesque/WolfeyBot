"""tools/release.py — the whole release chore in one allowlisted command.

Bumps ``version.py``, prepends a CHANGELOG entry (title + body from a notes
file, so the prose is written with the Write tool — no heredoc), regenerates
every turn-1 snapshot (restamping headers), and runs the full test suite.
Replaces the 4-step manual sequence that cost an approval prompt per step.

    .venv\\Scripts\\python.exe tools/release.py 0.43.0 --notes path/to/notes.md

The notes file is the markdown BODY of the entry (everything under the
``## <version> — <date>`` heading), written beforehand with the Write tool.
Committing stays a separate, deliberate ``git add`` + ``git commit -F``
(both allowlisted).
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_VERSION_FILE = os.path.join(ROOT, "version.py")
_CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Version bump + changelog + snapshots + suite.")
    ap.add_argument("version", help="new version, e.g. 0.43.0")
    ap.add_argument("--notes", required=True,
                    help="file containing the changelog entry body (markdown)")
    ap.add_argument("--no-tests", action="store_true",
                    help="skip the pytest run (rarely wanted)")
    args = ap.parse_args(argv)
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if not re.fullmatch(r"\d+\.\d+\.\d+", args.version):
        raise SystemExit(f"not a version: {args.version!r}")

    # 1. version.py
    with open(_VERSION_FILE, encoding="utf-8") as f:
        vtext = f.read()
    new_vtext, n = re.subn(r'__version__ = "[^"]+"',
                           f'__version__ = "{args.version}"', vtext)
    if n != 1:
        raise SystemExit("version.py: __version__ line not found")
    with open(_VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(new_vtext)

    # 2. CHANGELOG entry
    notes_path = args.notes if os.path.isabs(args.notes) else os.path.join(ROOT, args.notes)
    with open(notes_path, encoding="utf-8") as f:
        body = f.read().strip()
    today = _dt.date.today().isoformat()
    entry = f"## {args.version} — {today}\n\n{body}\n\n"
    with open(_CHANGELOG, encoding="utf-8") as f:
        ctext = f.read()
    header = "# WolfeyBot Changelog\n\n"
    if not ctext.startswith(header):
        raise SystemExit("CHANGELOG.md: unexpected header")
    with open(_CHANGELOG, "w", encoding="utf-8") as f:
        f.write(header + entry + ctext[len(header):])

    # 3. snapshots (restamps the version header; prints the decision triage)
    from tools.regen_snapshots import main as regen
    regen([])

    # 4. suite
    if not args.no_tests:
        r = subprocess.run([os.path.join(ROOT, ".venv", "Scripts", "pytest"), "-q"],
                           cwd=ROOT, capture_output=True, text=True)
        tail = (r.stdout or "").strip().splitlines()[-1:] or ["(no output)"]
        print(f"pytest: {tail[0]}")
        if r.returncode != 0:
            raise SystemExit("TEST SUITE FAILED — release not clean")

    print(f"Release {args.version} prepared: version.py + CHANGELOG + snapshots"
          f"{'' if args.no_tests else ' + suite green'}. Commit with git commit -F.")


if __name__ == "__main__":
    main()
