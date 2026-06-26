"""tools/run_games.py — One-shot "kick off N games" pipeline.

Runs a batch of ladder games on the latest meta-team version, then generates the
report and commits + pushes the resulting data — no intervention in between:

    .venv\\Scripts\\python.exe tools/run_games.py 50      # 50 games (default 50)

Steps, in order:
  1. main.py --team meta-team@<latest> --max-games N   (latest = highest
     teams/meta-team/v*.txt)
  2. tools/latest_meta_report.py                        (report on the new data)
  3. tools/commit_push_data.py                          (commit + push data only)

Each step inherits stdout so progress is visible; a failing step aborts the rest.
Run it in the background for long batches — when it finishes, the report is
written and the data is already pushed.
"""
import os
import re
import sys
import glob
import argparse
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable   # the venv python running this script


def latest_team_version():
    """Highest ``vN`` among ``teams/meta-team/v*.txt`` (e.g. 'v6')."""
    best, best_n = None, -1
    for p in glob.glob(os.path.join(ROOT, "teams", "meta-team", "v*.txt")):
        m = re.match(r"v(\d+)$", os.path.splitext(os.path.basename(p))[0])
        if m and int(m.group(1)) > best_n:
            best, best_n = f"v{m.group(1)}", int(m.group(1))
    return best


def _step(label, *cmd):
    print(f"\n=== {label} ===", flush=True)
    subprocess.run([PY, *cmd], cwd=ROOT, check=True)


def main():
    ap = argparse.ArgumentParser(description="Run N games, report, commit+push.")
    ap.add_argument("n", type=int, nargs="?", default=50,
                    help="number of games to play (default 50)")
    args = ap.parse_args()

    tv = latest_team_version()
    if tv is None:
        raise SystemExit("No teams/meta-team/v*.txt found.")
    team = f"meta-team@{tv}"

    _step(f"Run {args.n} games ({team})",
          "main.py", "--team", team, "--max-games", str(args.n))
    _step("Generate report", "tools/latest_meta_report.py")
    _step("Commit + push data", "tools/commit_push_data.py")
    print("\nPipeline complete.", flush=True)


if __name__ == "__main__":
    main()
