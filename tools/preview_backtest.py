"""tools/preview_backtest.py — replay logged team previews through the CURRENT
select_team/select_leads and compare against what was actually played.

For every battle log with a recorded ``preview`` under the given dir/glob, run
the current preview pipeline on the same opponent six and report how the bring
and lead choices shift — with each historical lead pair's actual W-L attached,
so a selector change can be sanity-checked against observed performance
("does it stop picking the pairs that lose?").

    .venv\\Scripts\\python.exe tools/preview_backtest.py "Battle Data/0.36.0/meta-team/v8"

NOTE: predictions use the CURRENT lead_stats/usage data, not what the games ran
with — this is a behavioural comparison of selectors, not a replay of history.
"""
from __future__ import annotations

import collections
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import team as team_mod                              # noqa: E402
from team_preview import select_team, select_leads   # noqa: E402


def main(argv=None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        raise SystemExit("usage: preview_backtest.py <logs-dir-or-glob>")
    base = args[0] if os.path.isabs(args[0]) else os.path.join(ROOT, args[0])
    files = (glob.glob(os.path.join(base, "**", "*.json"), recursive=True)
             if os.path.isdir(base) else glob.glob(base))
    files = [f for f in files if "lead_stats" not in f]

    old_leads = collections.Counter()
    new_leads = collections.Counter()
    lead_record: dict[tuple, list[int]] = collections.defaultdict(lambda: [0, 0])
    bring_old = collections.Counter()
    bring_new = collections.Counter()
    n = agree_bring = agree_leads = 0
    team_spec = None

    for path in sorted(files):
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception:
            continue
        pv = d.get("preview") or {}
        opp = pv.get("opp") or []
        bring = pv.get("bring") or []
        if len(opp) < 2 or len(bring) < 2:
            continue
        spec = f"{d.get('team')}@{d.get('team_version')}"
        if spec != team_spec:
            team_mod.set_active_team(spec)
            team_mod.get_team(reload=True)
            team_spec = spec
        members = team_mod.get_team()

        slots = select_team(opp, members, n=len(bring))
        slots = select_leads(slots, members, opp)
        new_bring = [members[i - 1].name for i in slots]

        old_pair = tuple(sorted(bring[:2]))
        new_pair = tuple(sorted(new_bring[:2]))
        old_leads[old_pair] += 1
        new_leads[new_pair] += 1
        won = d.get("outcome") == "win"
        lead_record[old_pair][0] += won
        lead_record[old_pair][1] += 1
        bring_old.update(bring)
        bring_new.update(new_bring)
        n += 1
        agree_bring += set(bring) == set(new_bring)
        agree_leads += old_pair == new_pair

    print(f"{n} games backtested  |  bring agreement {agree_bring}/{n}  |  "
          f"lead-pair agreement {agree_leads}/{n}\n")
    print(f"{'lead pair':38} {'played':>7} {'(W-L)':>8} {'new picks':>10}")
    for pair in sorted(set(old_leads) | set(new_leads),
                       key=lambda p: -(old_leads[p] + new_leads[p])):
        w, g = lead_record.get(pair, [0, 0])
        rec = f"{w}-{g - w}" if g else "-"
        print(f"{' + '.join(pair):38} {old_leads[pair]:>7} {rec:>8} "
              f"{new_leads[pair]:>10}")
    print(f"\n{'mon':20} {'brought (old)':>14} {'brought (new)':>14}")
    for mon in sorted(set(bring_old) | set(bring_new),
                      key=lambda m: -bring_old[m]):
        print(f"{mon:20} {bring_old[mon]:>14} {bring_new[mon]:>14}")


if __name__ == "__main__":
    main()
