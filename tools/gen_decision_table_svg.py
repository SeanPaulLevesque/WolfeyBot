"""tools/gen_decision_table_svg.py — render the per-action weight table as an SVG.

GitHub strips all CSS from markdown (no control over table width / padding / page
margins), so a 12-column HTML table overflows into a horizontal scrollbar there.
An SVG sidesteps that entirely: it is an image with pixel-exact width and font,
so it never scrolls and renders identically on GitHub, locally, and in dark mode.

The table content lives in ``ROWS`` below — edit a value/note and re-run:

    .venv\\Scripts\\python.exe tools/gen_decision_table_svg.py

Output: ``docs/decision_weights.svg`` (embedded by docs/DECISION_ARCHITECTURE.md).
Light/dark colours are driven by an embedded ``@media (prefers-color-scheme)``
block, which browsers honour when the SVG is loaded as an image.
"""
from __future__ import annotations

import html
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

# The numeric weights are read LIVE from the engine so the table can never
# drift from decision/modules.py — edit a constant there, re-run this, done.
from decision.modules import (  # noqa: E402
    DamageOutputModule as _Dmg, ThreatEliminationModule as _Threat,
    DoomedModule as _Doom, PriorityKillModule as _PKill,
    PriorityBlockModule as _PBlock, ProtectValueModule as _Prot,
    EndgameStallModule as _End, TurnOrderModule as _TO,
    OppProtectRecencyModule as _OPR, ConsecutiveProtectModule as _CP,
    FakeOutModule as _FO, FieldConditionModule as _FC,
    SwitchTempoModule as _ST,
    SwitchEscapeModule as _SE, SwitchDangerModule as _SDg,
    DoublingAdjuster as _Dbl, OverkillAdjuster as _Ovk,
    PartnerClearsAdjuster as _PC, CoordinationAdjuster as _Coord,
    SETUP_URGENCY, SETUP_DENIAL, BOOST_TARGET_FACTOR,
)


def _x(v: float) -> str:
    """Format a multiplier as a table cell, e.g. 2.5 -> '×2.5', 0.0 -> '×0'."""
    return f"×{v:g}"


OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "decision_weights.svg"

# ── Table content (the source of truth — edit here, then re-run) ───────────────
# Each row: (num, name, atk, tail, note)
#   atk  = ("span6", text)            value spans all six attack columns
#        | ("span3", slot1, slot2)    one value per Target-Slot group (3 cols each)
#   tail = [protect, switch1, switch2]   each a str, or (str, span) to merge cells
SECTION = "__section__"

# Numeric cells reference the LIVE engine constants (via _x / f-strings) so a
# weight change in decision/modules.py flows straight into the table on re-run.
# The prose in the Note column is hand-written (not derivable from a number).
_TURN_ORDER = " · ".join(f"pos {k} {_x(v)}"
                         for k, v in sorted(_TO._MULTIPLIERS.items()))

ROWS = [
    ("—",   "Starting Weight",        ("span6", "1"),                 ["1", "1", "1"],
     "All options equally likely to start"),
    ("1",   "Predicted Damage Dealt",
     ("cells", f"×({_Dmg.DAMAGE_INTERCEPT:g} + d×{_Dmg.DAMAGE_SLOPE:g})"), ["-", "—", "—"],
     "d = median damage roll as a fraction of the target's current HP, capped at 1.0 — "),
    ("2",   "Score A Guaranteed Kill", ("span6", _x(_Threat.GUARANTEED_OHKO)), ["—", "—", "—"],
     "Lowest damage roll ≥ the target's HP"),
    ("3",   "Die Before Acting",      ("span6", _x(_Doom.DOOMED_FACTOR)), ["—", "—", "—"],
     "A faster threat will kill us before we act (priority aware)"),
    ("4",   "Priority Kill",          ("span6", _x(_PKill.PRIORITY_KILL_FACTOR)), ["—", "—", "—"],
     "If one of our priority moves can score a kill"),
    ("5",   "Priority Block",         ("span6", _x(_PBlock.BLOCK_FACTOR)), ["—", "—", "—"],
     "Cancel priority attacks while an opponent has Armor Tail / Queenly Majesty on the field"),
    ("6",   "Incoming Kill",          ("span6", "—"),                 [_x(_Prot.THREATENED_FACTOR), "—", "—"],
     "An opponent's max roll kills this mon at its current HP"),
    ("7.a", "1v1 Endgame",            ("span6", "—"),                 [_x(_End.ENDGAME_1V1_FACTOR), "—", "—"],
     "Protect stalling in 1v1 only delays"),
    ("7.b", "2v1 Endgame",            ("span6", "—"),                 [_x(_End.ADVANTAGE_2V1_FACTOR), "—", "—"],
     "Protect stalling in 2v1 can't improve the outcome"),
    ("8",   "Turn Order",             ("span6", _TURN_ORDER),
     ["—", "—", "—"], "pos = Our rank in the 4-mon turn order"),
    ("9",   "Setup Urgency",          ("span3", _x(SETUP_URGENCY), _x(SETUP_URGENCY)), ["—", "—", "—"],
     "A setter is on the field, but their effect isn't active *"),
    ("10",  "Setup Denial",           ("span3", _x(SETUP_DENIAL), _x(SETUP_DENIAL)), ["—", "—", "—"],
     "OHKOs a setter *"),
    ("11.a", "target Protected last turn (Slot 1)",
     ("span3", _x(_OPR.PROTECTED_BOOST), "—"), ["—", "—", "—"],
     "the Slot-1 target used Protect last turn, so it can't Protect again"),
    ("11.b", "target Protected last turn (Slot 2)",
     ("span3", "—", _x(_OPR.PROTECTED_BOOST)), ["—", "—", "—"],
     "the Slot-2 target used Protect last turn, so it can't Protect again"),
    ("12",  "I used Protect last turn", ("span6", "—"),               [_x(_CP.CONSECUTIVE_PENALTY), "—", "—"],
     "consecutive Protect"),
    ("13",  "Fake Out threatened",    ("merge6", _x(_FO.ATTACK_DISCOUNT)),
     [_x(_FO.PROTECT_BOOST), "—", "—"],
     "a fresh Fake Out user is on the field"),
    ("14",  "Field Condition stall",  ("span6", "—"),                 [_x(_FC.STALL_FACTOR), "—", "—"],
     "opp Trick Room / Tailwind has 1 or 3 turns left"),
    ("15",  "redirection hedge",      ("cells", "×d (to redirector)"), ["—", "—", "—"],
     "Rage Powder / Follow Me user active; hedge our attack on the possibility of redirection"),
    ("16",  "Switch tempo",           ("span6", "—"),                 ["—", _x(_ST.TEMPO_FACTOR), _x(_ST.TEMPO_FACTOR)],
     "flat cost of switching — forfeit the turn + concede a free hit"),
    ("17",  "Switch offense",         ("span6", "—"),                 ["—", "×(1+g)", "×(1+g)"],
     "g = the switch-in's best-damage gain over the mon staying in (floored at 0)"),
    ("18",  "Switch escape",          ("span6", "—"),
     ["—", _x(_SE.ESCAPE_FACTOR), _x(_SE.ESCAPE_FACTOR)],
     "bail a mon facing a connecting OHKO into a switch-in that survives"),
    ("19",  "Switch danger",          ("span6", "—"),
     ["—", _x(_SDg.DANGER_FACTOR), _x(_SDg.DANGER_FACTOR)],
     "soft discount when the switch-in is itself OHKO'd — not a veto"),
    ("20",  "Boosted target",         ("span6", f"×(1 + {BOOST_TARGET_FACTOR:g}×stages)"), ["—", "—", "—"],
     "attacks into a stat-boosted opponent, per positive stage on the target — 1 stage ×1.4, "
     "2 ×1.8; punish the snowball before it rolls"),
    (SECTION, "Phase 2 — joint adjusters (applied to the chosen pair)", None, None, None),
    ("J1",  "doubling up",            ("span6", _x(_Dbl.DOUBLING_FACTOR)), ["—", "—", "—"],
     "flat penalty when both slots attack the same target — the spread-your-damage tax"),
    ("J2",  "overkill",               ("span6", _x(_Ovk.FACTOR)),     ["—", "—", "—"],
     "one slot already guarantees the OHKO on the shared target → near-veto the other "
     "(wasteful) doubler, so the pair that spreads onto the survivor wins. Composes on top of J1"),
    ("J2b", "joint setup denial",
     ("span6", f"×{1 / _Dbl.DOUBLING_FACTOR:g} × {_x(SETUP_DENIAL)}"), ["—", "—", "—"],
     f"both attack the same SETTER (TR/TW), neither solo-OHKOs it, but summed min rolls kill it "
     f"and both attacks resolve before it moves → doubling tax waived (×{1 / _Dbl.DOUBLING_FACTOR:g}) "
     f"+ setup denial ({_x(SETUP_DENIAL)})"),
    ("J3",  "attack alongside partner", ("span6", "—"),               [_x(_Coord.SPLIT_PENALTY), "—", "—"],
     "a gratuitous lone Protect (no real OHKO/stall reason, e.g. only a Fake Out nudge) "
     "beside an attacking partner — favour the double-attack"),
    ("J4",  "Fake Out absorbed (free partner)",
     ("span6", _x(1 / _FO.ATTACK_DISCOUNT)), [_x(1 / _FO.PROTECT_BOOST), "—", "—"],
     "when either slot attacks, the partner's Fake-Out multiplier above is divided back out "
     "(attack un-halved, Protect un-boosted) — a pair pays the Fake-Out adjustment once, never twice"),
    ("J5",  "switch collision",       ("span6", "—"),                 ["—", ("×0", 2)],
     "both slots switch to the same bench mon → that pair is vetoed"),
    ("J6",  "Partner Clears",         ("span6", "—"),                 [_x(_PC.PARTNER_KO_FACTOR), "—", "—"],
     "one slot Protects against a connecting OHKO and the partner's chosen attack guaranteed-"
     "OHKOs that threatener → Protect so we survive while the partner removes it "
     "(was phase-1 \"Threat Clear\"; it's a cross-slot question, so it's phase 2)"),
]

FOOTNOTE = "*  setup = Trick Room / Tailwind / a defensive-boost move"

# ── Geometry ──────────────────────────────────────────────────────────────────
# Column order: num, name, a1, a2, a3, a4, a5, a6, protect, sw1, sw2, note
W = [26, 130, 52, 52, 52, 52, 52, 52, 50, 68, 68, 232]
X = [0]
for w in W:
    X.append(X[-1] + w)
TOTAL_W = X[-1]

FS       = 11      # body / header font
FS_NOTE  = 10.5    # note column
LINE_H   = 14
PAD_X    = 6
HEADER_H = 40      # two stacked header rows
ROW_MIN  = 22

# Approx character width for wrapping (proportional sans ~0.55em, +slack).
def _wrap(text: str, col_w: int, fs: float) -> list[str]:
    avail = col_w - 2 * PAD_X
    max_chars = max(4, int(avail / (fs * 0.56)))
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = word if not cur else cur + " " + word
        if len(cand) <= max_chars:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def _esc(s: str) -> str:
    return html.escape(s, quote=True)


def _comment(s: str) -> str:
    """Sanitise text for an XML comment: `--` is illegal inside `<!-- -->`."""
    return s.replace("--", "—")


def _text(x, y, s, *, cls="tx", anchor="middle", fs=FS, bold=False):
    weight = ' font-weight="600"' if bold else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" class="{cls}" font-size="{fs}" '
            f'text-anchor="{anchor}"{weight}>{_esc(s)}</text>')


def _vline(x, y0, y1):
    return f'<line x1="{x:.1f}" y1="{y0:.1f}" x2="{x:.1f}" y2="{y1:.1f}" class="bd"/>'


def _hline(y, x0=0, x1=None):
    x1 = TOTAL_W if x1 is None else x1
    return f'<line x1="{x0:.1f}" y1="{y:.1f}" x2="{x1:.1f}" y2="{y:.1f}" class="bd"/>'


def _fits(text: str, col_w: int) -> bool:
    """Does *text* fit one attack column at the body font (so we can show it as a
    distinct per-attack cell rather than merging across the slot)?"""
    return len(text) * FS * 0.56 <= col_w - 4


def _row_cells(atk, tail):
    """Yield (x, width, text, align) cells for the value columns of a row.

    Explicit per-row attack rendering (set in ROWS):
      ``cells``  — six individual attack cells (per-action grid)
      ``merge6`` — one cell spanning all six attack columns
      ``span3``  — one cell per Target-Slot group (merged across that slot)
      ``span6``  — auto: per-cell if the value fits one column, else one span
                   (the default for rows not explicitly called out)
    Overflow is not policed — column widths in ``W`` are tuned by hand."""
    mode = atk[0]
    if mode == "cells":
        for c in range(2, 8):
            yield (X[c], W[c], atk[1], "mid")
    elif mode == "merge6":
        yield (X[2], X[8] - X[2], atk[1], "mid")
    elif mode == "span3":
        yield (X[2], X[5] - X[2], atk[1], "mid")
        yield (X[5], X[8] - X[5], atk[2], "mid")
    else:  # span6 — auto
        if _fits(atk[1], W[2]):
            for c in range(2, 8):
                yield (X[c], W[c], atk[1], "mid")
        else:
            yield (X[2], X[8] - X[2], atk[1], "mid")
    # tail: protect(8), sw1(9), sw2(10)
    col = 8
    for entry in tail:
        if isinstance(entry, tuple):
            txt, span = entry
        else:
            txt, span = entry, 1
        yield (X[col], X[col + span] - X[col], txt, "mid")
        col += span


def build() -> str:
    body: list[str] = []
    y = HEADER_H

    for row in ROWS:
        num, name, atk, tail, note = row
        if num == SECTION:
            body.append(f'<!-- ══ {_comment(name)} ══ -->')
            h = ROW_MIN
            body.append(f'<rect x="0" y="{y:.1f}" width="{TOTAL_W}" height="{h}" class="sec"/>')
            body.append(_hline(y))
            body.append(_text(PAD_X, y + h / 2 + 4, name, cls="tx", anchor="start",
                              fs=FS, bold=True))
            body.append(_vline(0, y, y + h))
            body.append(_vline(TOTAL_W, y, y + h))
            y += h
            continue

        body.append(f'<!-- row {num}: {_comment(name)} -->')
        name_lines = _wrap(name, W[1], FS)
        note_lines = _wrap(note, W[11], FS_NOTE)
        h = max(ROW_MIN, LINE_H * max(len(name_lines), len(note_lines)) + 8)
        body.append(_hline(y))

        # # and name
        body.append(_text(X[0] + W[0] / 2, y + h / 2 + 4, num, fs=FS))
        ny = y + h / 2 - LINE_H * (len(name_lines) - 1) / 2 + 4
        for i, ln in enumerate(name_lines):
            body.append(_text(X[1] + PAD_X, ny + i * LINE_H, ln, anchor="start", fs=FS))

        # value cells
        for cx, cw, txt, _align in _row_cells(atk, tail):
            body.append(_text(cx + cw / 2, y + h / 2 + 4, txt, fs=FS))

        # note (left aligned, wrapped)
        nty = y + h / 2 - LINE_H * (len(note_lines) - 1) / 2 + 4
        for i, ln in enumerate(note_lines):
            body.append(_text(X[11] + PAD_X, nty + i * LINE_H, ln,
                              cls="tx", anchor="start", fs=FS_NOTE))

        # per-row vertical cell edges (respect spans)
        edges = {X[0], X[1], X[11], X[11 + 1], TOTAL_W}
        for cx, cw, _t, _a in _row_cells(atk, tail):
            edges.add(cx); edges.add(cx + cw)
        for ex in edges:
            body.append(_vline(ex, y, y + h))
        y += h

    body.append(_hline(y))  # bottom border
    body.append(_text(0, y + 16, FOOTNOTE, cls="tx", anchor="start", fs=FS_NOTE))
    total_h = y + 22

    # ── Header (two rows: groups, then attack sub-labels) ─────────────────────
    hdr: list[str] = [f'<rect x="0" y="0" width="{TOTAL_W}" height="{HEADER_H}" class="hd"/>']
    half = HEADER_H / 2
    # rowspan-2 single headers
    for idx, label in ((0, "#"), (1, ""), (8, "Protect"), (9, "Switch 1"),
                       (10, "Switch 2"), (11, "Note")):
        if label:
            hdr.append(_text((X[idx] + X[idx + 1]) / 2, HEADER_H / 2 + 4, label, bold=True))
    # grouped attack headers (top half)
    hdr.append(_text((X[2] + X[5]) / 2, half / 2 + 4, "Target Slot 1", bold=True))
    hdr.append(_text((X[5] + X[8]) / 2, half / 2 + 4, "Target Slot 2", bold=True))
    # attack sub-labels (bottom half)
    for i, idx in enumerate((2, 3, 4, 5, 6, 7)):
        hdr.append(_text((X[idx] + X[idx + 1]) / 2, half + half / 2 + 4,
                        f"Attack {i % 3 + 1}", bold=True))
    # header borders
    hdr.append(_hline(0)); hdr.append(_hline(HEADER_H)); hdr.append(_hline(half, X[2], X[8]))
    for idx in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11):
        hdr.append(_vline(X[idx], 0, HEADER_H))
    hdr.append(_vline(TOTAL_W, 0, HEADER_H))

    style = (
        '<style>\n'
        '    .bg { fill: #ffffff; }\n'
        '    .hd { fill: #f6f8fa; }\n'
        '    .sec{ fill: #eaeef2; }\n'
        '    .tx { fill: #1f2328; font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }\n'
        '    .bd { stroke: #d0d7de; stroke-width: 1; }\n'
        '    @media (prefers-color-scheme: dark) {\n'
        '      .bg { fill: #0d1117; }\n'
        '      .hd { fill: #161b22; }\n'
        '      .sec{ fill: #21262d; }\n'
        '      .tx { fill: #e6edf3; }\n'
        '      .bd { stroke: #30363d; }\n'
        '    }\n'
        '  </style>'
    )

    # One element per line, indented inside <svg>, with the row comments already
    # threaded through `body` — so the file is diff-friendly and hand-readable
    # (it is generated, but a clean diff makes weight-table changes reviewable).
    elements = (
        [style,
         f'<rect x="0" y="0" width="{TOTAL_W}" height="{total_h:.0f}" class="bg"/>',
         '',
         '<!-- column header -->']
        + hdr
        + ['', '<!-- table body + notes -->']
        + body
    )
    inner = "\n  ".join(elements)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{TOTAL_W}" '
        f'height="{total_h:.0f}" viewBox="0 0 {TOTAL_W} {total_h:.0f}" '
        f'font-family="sans-serif">\n'
        f'  {inner}\n'
        f'</svg>\n'
    )


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(OUT.parent.parent)}  ({TOTAL_W}px wide)")


if __name__ == "__main__":
    main()
