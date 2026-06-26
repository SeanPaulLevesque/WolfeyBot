"""tools/latest_meta_report.py — Zero-argument meta-team report generator.

Finds the most recent meta-team battle-data folder under ``Battle Data/`` (the
directory holding the single most-recently-modified battle log) and writes the
standard team report to ``reports/meta-team_<team_version>_<engine_version>.md``.

No arguments, no prompts, no judgement calls — run it bare:

    .venv\\Scripts\\python.exe tools/latest_meta_report.py

It reuses the pure helpers in :mod:`tools.team_report`, so the report content is
identical to running ``team_report.py`` by hand on that folder — this script
only does the "which folder is latest" lookup so a human (or the agent) doesn't
have to.

Layout assumed (what the bot writes named-team logs to):
    Battle Data/<engine_version>/meta-team/<team_version>/*.json
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
TEAM_NAME = "meta-team"


def latest_meta_dir():
    """Return ``(dir, engine_version, team_version)`` for the meta-team data
    folder holding the most-recently-modified battle log, or ``(None, None,
    None)`` if there is no meta-team data."""
    pattern = os.path.join(BATTLE_DATA, "*", TEAM_NAME, "*", "*.json")
    files = glob.glob(pattern)
    if not files:
        return None, None, None
    newest = max(files, key=os.path.getmtime)
    d = os.path.dirname(newest)
    parts = d.replace("\\", "/").split("/")
    # .../Battle Data/<engine_version>/meta-team/<team_version>
    return d, parts[-3], parts[-1]


def main():
    d, engine_version, team_version = latest_meta_dir()
    if d is None:
        print(f"No {TEAM_NAME} battle data found under Battle Data/.")
        sys.exit(1)

    files = find_log_files(d)
    games = [json.load(open(f, encoding="utf-8")) for f in files]
    if not games:
        print(f"No battle logs in {d}.")
        sys.exit(1)

    # Prefer the path-derived team/version; fall back to log-derived if the
    # layout is unusual.
    derived_name, derived_tv = derive_team_meta(files)
    team_name = derived_name or TEAM_NAME
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
