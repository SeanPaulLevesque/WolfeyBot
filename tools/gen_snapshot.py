"""tools/gen_snapshot.py — render a decision-snapshot for a (scenario × team).

A *scenario* (scenarios/<name>.py) defines team-parameterised board states; this
driver selects the team, asks the scenario to render, and writes the result to
``snapshots/<scenario>/<team>.md``.  That file is both a human-readable table and
a regression baseline (guarded by tests/test_turn1_decisions.py).

Usage (from repo root):
    .venv\\Scripts\\python.exe tools/gen_snapshot.py --scenario turn1_openings --team baseline
    .venv\\Scripts\\python.exe tools/gen_snapshot.py --scenario turn1_openings --team meta-team@v1

``--team baseline`` (the default) uses the frozen regression roster
(snapshots/baseline_team.txt, via team.py's no-selection fallback); any other
value resolves a named team from teams/.
"""
import argparse
import importlib
import pathlib
import sys

# Allow running as `python tools/gen_snapshot.py` from the repo root.
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import team as team_mod                       # noqa: E402
from decision.modules import make_engine      # noqa: E402
from version import __version__               # noqa: E402

SNAPSHOTS_DIR = _REPO_ROOT / "snapshots"


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Generate a decision-snapshot for a scenario × team.")
    ap.add_argument("--scenario", default="turn1_openings",
                    help="scenario module under scenarios/ (default: %(default)s)")
    ap.add_argument("--team", default="baseline",
                    help="'baseline' (frozen regression roster) or 'name@vN' (default: %(default)s)")
    args = ap.parse_args(argv)

    # Select the team: 'baseline' clears the selection so team.py falls back to
    # snapshots/baseline_team.txt; anything else resolves a named team.
    if args.team == "baseline":
        team_mod.set_active_team(None)
        team_label = "baseline"
    else:
        name, ver = team_mod.set_active_team(args.team)
        team_label = f"{name}@{ver}"
    team_mod.get_team(reload=True)             # rebuild cache for the selected roster

    scenario = importlib.import_module(f"scenarios.{args.scenario}")
    markdown = scenario.render(make_engine(), __version__)

    out_path = SNAPSHOTS_DIR / args.scenario / f"{team_label}.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"Written {out_path.relative_to(_REPO_ROOT)}")


if __name__ == "__main__":
    main()
