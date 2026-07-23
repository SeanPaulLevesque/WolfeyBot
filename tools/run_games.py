"""tools/run_games.py — One-shot "kick off N games" pipeline, for ANY named team.

Runs a batch of ladder games, then generates the report and commits + pushes
the resulting data — no intervention in between:

    .venv\\Scripts\\python.exe tools/run_games.py

Fixed-invocation mode (no args): reads ``tools/scratch/run_games.json``:

    {"team": "off-meta-team", "version": "v4", "n": 50}

``team`` defaults to "meta-team"; ``version`` defaults to that team's highest
``teams/<team>/v*.txt``; ``n`` defaults to 50. Omit the spec file entirely to
get the old zero-config behaviour (latest meta-team version, 50 games).

Steps, in order:
  1. main.py --team <team>@<version> --max-games N
  2. tools/latest_team_report.py   (report on whichever team/data is newest)
  3. tools/commit_push_data.py     (commit + push data only)

Each step inherits stdout so progress is visible; a failing step aborts the
rest. Run it in the background for long batches — when it finishes, the report
is written and the data is already pushed. To stop a running batch cleanly
(finish the current game, no forfeit), drop a file at ``tools/scratch/stop``.
"""
import os
import re
import sys
import glob
import argparse
import json
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable   # the venv python running this script
SPEC = os.path.join(ROOT, "tools", "scratch", "run_games.json")


def latest_team_version(team_name: str):
    """Highest ``vN`` among ``teams/<team_name>/v*.txt`` (e.g. 'v6')."""
    best, best_n = None, -1
    for p in glob.glob(os.path.join(ROOT, "teams", team_name, "v*.txt")):
        m = re.match(r"v(\d+)$", os.path.splitext(os.path.basename(p))[0])
        if m and int(m.group(1)) > best_n:
            best, best_n = f"v{m.group(1)}", int(m.group(1))
    return best


def _step(label, *cmd):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([PY, *cmd], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser(description="Run N games, report, commit+push.")
    ap.add_argument("n", type=int, nargs="?",
                    help="number of games to play (default: from spec file, else 50)")
    ap.add_argument("--team", help="named team (default: from spec file, else meta-team)")
    ap.add_argument("--version", help="team version, e.g. v4 (default: highest available)")
    args = ap.parse_args()

    spec = {}
    if os.path.exists(SPEC):
        with open(SPEC, encoding="utf-8") as f:
            spec = json.load(f)

    team_name = args.team or spec.get("team") or "meta-team"
    version = args.version or spec.get("version") or latest_team_version(team_name)
    n = args.n if args.n is not None else spec.get("n", 50)

    if version is None:
        raise SystemExit(f"No teams/{team_name}/v*.txt found.")
    team = f"{team_name}@{version}"

    stop_file = os.path.join(ROOT, "tools", "scratch", "stop")
    if os.path.exists(stop_file):
        os.remove(stop_file)   # stale leftover from a prior run — don't stop immediately

    _step(f"Run {n} games ({team})",
          "main.py", "--team", team, "--max-games", str(n))
    _step("Generate report", "tools/latest_team_report.py")
    _step("Commit + push data", "tools/commit_push_data.py")
    print("\nPipeline complete.", flush=True)


if __name__ == "__main__":
    main()
