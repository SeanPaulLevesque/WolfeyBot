"""tools/regen_snapshots.py — regenerate every turn-1 snapshot and triage the diff.

One command replaces the regen loop + the inline diff-classification script:

    .venv\\Scripts\\python.exe tools/regen_snapshots.py

* Regenerates ``snapshots/turn1_openings/<team>.md`` for every team that already
  has a snapshot file (self-updating: add a team's snapshot once and it's
  included in every future regen).
* Diffs each file against ``git HEAD`` and classifies the changed cells:
  **decision changes** (the chosen move/target differs, ignoring weight numbers)
  vs **weight-only** (same decision, different score) — the split that matters
  for the review-before-commit rule.

NOTE: this rewrites the snapshot files in the working tree. Per the testing
workflow, regenerated snapshots are only *committed* after the behavior change
that produced the diff has been reviewed and approved.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.gen_snapshot import main as gen_main  # noqa: E402

SNAP_DIR = ROOT / "snapshots" / "turn1_openings"
_CELL = re.compile(r"^\| (\d+\.\d+) \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$")


def _strip_weights(line: str) -> str:
    return re.sub(r"`[\d.]+`", "`W`", line)


def _cells(text: str) -> dict[str, str]:
    """{cell_id: full row line} for every decision cell in a snapshot."""
    out = {}
    for line in text.splitlines():
        m = _CELL.match(line)
        if m:
            out[m.group(1)] = line
    return out


def _head_text(rel_posix: str) -> str:
    """File content at git HEAD ('' if the file is new)."""
    r = subprocess.run(["git", "show", f"HEAD:{rel_posix}"],
                       capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    return r.stdout if r.returncode == 0 else ""


def main(argv=None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    teams = sorted(p.stem for p in SNAP_DIR.glob("*.md"))
    if not teams:
        raise SystemExit(f"no snapshots found under {SNAP_DIR}")

    for t in teams:
        gen_main(["--scenario", "turn1_openings", "--team", t])

    grand_dec = grand_w = 0
    decision_lines: list[str] = []
    for t in teams:
        path = SNAP_DIR / f"{t}.md"
        rel = path.relative_to(ROOT).as_posix()
        old = _cells(_head_text(rel))
        new = _cells(path.read_text(encoding="utf-8"))
        if not old:
            print(f"{t}: NEW FILE ({len(new)} cells, no HEAD baseline)")
            continue
        dec = w_only = 0
        for cid in sorted(set(old) | set(new), key=lambda c: [int(x) for x in c.split(".")]):
            o, n = old.get(cid, ""), new.get(cid, "")
            if o == n:
                continue
            if _strip_weights(o) == _strip_weights(n):
                w_only += 1
            else:
                dec += 1
                decision_lines.append(f"[{t}] OLD {o.strip()}")
                decision_lines.append(f"[{t}] NEW {n.strip()}")
        grand_dec += dec
        grand_w += w_only
        print(f"{t}: {dec} decision changes, {w_only} weight-only")

    print(f"\nTOTAL vs HEAD: {grand_dec} decision changes, {grand_w} weight-only")
    if decision_lines:
        cap = 60
        print("\n=== decision changes (move/target differs) ===")
        for line in decision_lines[:cap * 2]:
            print(line)
        if len(decision_lines) > cap * 2:
            print(f"... and {(len(decision_lines) - cap * 2) // 2} more")
        print("\nReview these before regenerating expectations / committing "
              "(testing rule: behavior changes need approval).")


if __name__ == "__main__":
    main()
