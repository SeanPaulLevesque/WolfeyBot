"""tools/latest_team_report.py — Zero-argument report generator for the latest
battle-data folder, whichever named team it belongs to.

Finds the single most-recently-modified battle log anywhere under
``Battle Data/`` (across every named team, not just meta-team) and writes the
standard team report to ``reports/<team>_<team_version>_<engine_version>.md``.

No arguments, no prompts, no judgement calls — run it bare:

    .venv\\Scripts\\python.exe tools/latest_team_report.py

It reuses the pure helpers in :mod:`tools.team_report`, so the report content is
identical to running ``team_report.py`` by hand on that folder — this script
only does the "which folder is latest" lookup so a human (or the agent) doesn't
have to.

Layout assumed (what the bot writes named-team logs to):
    Battle Data/<engine_version>/<team_name>/<team_version>/*.json
"""
import os
import sys
import json
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.team_report import (
    find_log_files, derive_team_meta, load_paste, build_markdown,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BATTLE_DATA = os.path.join(ROOT, "Battle Data")


def latest_team_dir():
    """Return ``(dir, engine_version, team_name, team_version)`` for the data
    folder holding the most-recently-modified battle log across EVERY named
    team, or ``(None, None, None, None)`` if there is no battle data at all."""
    pattern = os.path.join(BATTLE_DATA, "*", "*", "*", "*.json")
    files = glob.glob(pattern)
    if not files:
        return None, None, None, None
    newest = max(files, key=os.path.getmtime)
    d = os.path.dirname(newest)
    parts = d.replace("\\", "/").split("/")
    # .../Battle Data/<engine_version>/<team_name>/<team_version>
    return d, parts[-3], parts[-2], parts[-1]


def main():
    d, engine_version, team_name, team_version = latest_team_dir()
    if d is None:
        print("No battle data found under Battle Data/.")
        sys.exit(1)

    files = find_log_files(d)
    games = [json.load(open(f, encoding="utf-8")) for f in files]
    if not games:
        print(f"No battle logs in {d}.")
        sys.exit(1)

    # Prefer the path-derived team/version; fall back to log-derived if the
    # layout is unusual.
    derived_name, derived_tv = derive_team_meta(files)
    team_name = team_name or derived_name
    team_version = team_version or derived_tv
    paste = load_paste(team_name, team_version)

    label = os.path.relpath(d, ROOT).replace("\\", "/")
    md = build_markdown(games, label, 0.15, team_name, team_version, paste)

    out_dir = os.path.join(ROOT, "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, f"{team_name}_{team_version}_{engine_version}.md")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(md)
    rel = os.path.relpath(out_file, ROOT).replace("\\", "/")
    print(f"Wrote {rel} ({len(games)} games) - {team_name} {team_version}, engine {engine_version}.")


if __name__ == "__main__":
    main()
