"""tools/commit_push_data.py — Zero-argument commit + push of battle-data artifacts.

Stages **only** the data artifacts that accumulate from running games and
generating reports — ``Battle Data/`` (battle logs + ``lead_stats.json``),
``elo_log.json``, and ``reports/`` — commits them with an auto-generated message,
and pushes. Code / docs / tests are never staged, so this can run unattended
(e.g. appended after a games + report run) without sweeping real changes into a
data commit or needing a human to write a message.

No arguments, no prompts, no judgement calls:

    .venv\\Scripts\\python.exe tools/commit_push_data.py

If nothing in the data paths changed it's a clean no-op (exit 0). Any modified
non-data files are reported as a non-blocking note and left untouched.
"""
import os
import sys
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# The only paths this script ever stages.  Everything else is left untouched.
DATA_PATHS = ["Battle Data", "elo_log.json", "reports"]


def _git(*args, check=True):
    """Run a git command at the repo root, returning stripped stdout."""
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"git {' '.join(args)} failed (exit {r.returncode}).")
    return r.stdout.strip()


def _auto_message(staged):
    """Build the commit message from the staged data paths."""
    logs = [s for s in staged
            if "/battle-" in s.replace("\\", "/") and s.endswith(".json")]
    if logs:
        # Parse engine/team from the newest log path:
        # Battle Data/<engine>/meta-team/<tv>/battle-...json
        parts = max(logs).replace("\\", "/").split("/")
        try:
            i = parts.index("Battle Data")
            engine, team, tv = parts[i + 1], parts[i + 2], parts[i + 3]
            return f"Battle data: +{len(logs)} logs ({team} {tv}, engine {engine})"
        except (ValueError, IndexError):
            return f"Battle data: +{len(logs)} logs"
    return "Update battle-data artifacts (reports / elo log)"


def main():
    # Note any non-data changes (informational; they are NOT committed).
    dirty = [l[3:] for l in _git("status", "--porcelain").splitlines() if l]
    non_data = [f for f in dirty
                if not any(f.strip('"').startswith(p) for p in DATA_PATHS)]

    _git("add", "--", *DATA_PATHS)
    staged = _git("diff", "--cached", "--name-only").splitlines()
    if not staged:
        print("No data changes to commit.")
        if non_data:
            print(f"  ({len(non_data)} non-data file(s) modified, left untouched.)")
        return

    msg = _auto_message(staged)
    _git("commit", "-m", msg)
    _git("push")
    print(f"Committed + pushed: {msg} ({len(staged)} file(s)).")
    if non_data:
        print(f"  ({len(non_data)} non-data file(s) modified, left untouched.)")


if __name__ == "__main__":
    main()
