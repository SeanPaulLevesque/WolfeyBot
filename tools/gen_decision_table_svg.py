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

OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "decision_weights.svg"

# ── Table content (the source of truth — edit here, then re-run) ───────────────
# Each row: (num, name, atk, tail, note)
#   atk  = ("span6", text)            value spans all six attack columns
#        | ("span3", slot1, slot2)    one value per Target-Slot group (3 cols each)
#   tail = [protect, switch1, switch2]   each a str, or (str, span) to merge cells
SECTION = "__section__"

ROWS = [
    ("—",   "Starting Weight",        ("span6", "1"),                 ["1", "1", "1"],
     "All options equally likely to start"),
    ("1",   "Predicted Damage Dealt", ("cells", "×(1 + d×2.0)"),      ["-", "—", "—"],
     "d = median damage roll as a fraction of the target's current HP, capped at 1.0 — "
     "overkill earns nothing (value saturates at lethal, so the joint pass routes by chip, "
     "not by which foe is overkilled hardest)"),
    ("2",   "Score A Guaranteed Kill", ("span6", "×5"),               ["—", "—", "—"],
     "Lowest damage roll ≥ the target's HP"),
    ("3",   "Die Before Acting",      ("span6", "×0.2"),              ["—", "—", "—"],
     "A faster threat will kill before we act (priority aware)"),
    ("4",   "Priority Kill",          ("span6", "×3.0"),              ["—", "—", "—"],
     "If one of our priority moves can score a kill"),
    ("5",   "Priority Block",         ("span6", "×0"),                ["—", "—", "—"],
     "Cancel priority attacks while an opponent has Armor Tail / Queenly Majesty on the field"),
    ("6",   "Incoming Kill",          ("span6", "—"),                 ["×2.5", "—", "—"],
     "An opponent's max roll kills this mon at its current HP"),
    ("7.a", "1v1 Endgame",            ("span6", "—"),                 ["×0.4", "—", "—"],
     "Protect stalling in 1v1 is net neutral"),
    ("7.b", "2v1 Endgame",            ("span6", "—"),                 ["×0.4", "—", "—"],
     "Protect stalling in 2v1 is net negative"),
    ("8",   "Turn Order",             ("span6", "pos 1 ×2.0 · pos 2 ×1.5 · pos 3 ×1.0 · pos 4 ×0.75"),
     ["—", "—", "—"], "pos = Our rank in the 4-mon turn order"),
    ("9",   "Setup Urgency",          ("span3", "×2.0", "×2.0"),      ["—", "—", "—"],
     "A setter is on the field, but their effect isn't active *"),
    ("10",  "Setup Denial",           ("span3", "×2.0", "×2.0"),      ["—", "—", "—"],
     "OHKOs a setter *"),
    ("11.a", "target Protected last turn (Slot 1)", ("span3", "×1.3", "—"), ["—", "—", "—"],
     "the Slot-1 target used Protect last turn, so it can't Protect again"),
    ("11.b", "target Protected last turn (Slot 2)", ("span3", "—", "×1.3"), ["—", "—", "—"],
     "the Slot-2 target used Protect last turn, so it can't Protect again"),
    ("12",  "I used Protect last turn", ("span6", "—"),               ["×0.2", "—", "—"],
     "consecutive Protect"),
    ("13",  "Fake Out threatened",    ("merge6", "×0.5"),             ["×3.0", "—", "—"],
     "a fresh Fake Out user is on the field"),
    ("14",  "Field Condition stall",  ("span6", "—"),                 ["×3.0", "—", "—"],
     "opp Trick Room / Tailwind has 1 or 3 turns left"),
    ("15",  "redirection hedge",      ("cells", "×d (to redirector)"), ["—", "—", "—"],
     "Rage Powder / Follow Me user active; hedge our attack on the possibility of redirection"),
    ("16",  "Switch tempo",           ("span6", "—"),                 ["—", "×0.8", "×0.8"],
     "flat cost of switching — forfeit the turn + concede a free hit"),
    ("17",  "Switch offense",         ("span6", "—"),                 ["—", "×(1+g)", "×(1+g)"],
     "g = the switch-in's best-damage gain over the mon staying in (floored at 0)"),
    ("18",  "Switch safety",          ("span6", "—"),                 ["—", "×4.0 / ×0.3", "×4.0 / ×0.3"],
     "×4.0 escape a connecting OHKO into a surviving switch-in; ×0.3 if the switch-in is itself OHKO'd"),
    (SECTION, "Phase 2 — joint adjusters (applied to the chosen pair)", None, None, None),
    ("J1",  "doubling up",            ("span6", "×0.4"),              ["—", "—", "—"],
     "flat penalty when both slots attack the same target — the spread-your-damage tax"),
    ("J2",  "overkill",               ("span6", "×0.05"),             ["—", "—", "—"],
     "one slot already guarantees the OHKO on the shared target → near-veto the other "
     "(wasteful) doubler, so the pair that spreads onto the survivor wins. Composes on top of J1"),
    ("J2b", "joint setup denial",      ("span6", "×2.5 × ×2.0"),      ["—", "—", "—"],
     "both attack the same SETTER (TR/TW), neither solo-OHKOs it, but summed min rolls kill it "
     "and both attacks resolve before it moves → doubling tax waived (×2.5) + setup denial (×2.0)"),
    ("J3",  "attack alongside partner", ("span6", "—"),               ["×0.5", "—", "—"],
     "a gratuitous lone Protect (no real OHKO/stall reason, e.g. only a Fake Out nudge) "
     "beside an attacking partner — favour the double-attack"),
    ("J4",  "Fake Out absorbed (free partner)", ("span6", "×2.0"),    ["×0.33", "—", "—"],
     "when either slot attacks, the partner's Fake-Out multiplier above is divided back out "
     "(attack un-halved, Protect un-boosted) — a pair pays the Fake-Out adjustment once, never twice"),
    ("J5",  "switch collision",       ("span6", "—"),                 ["—", ("×0", 2)],
     "both slots switch to the same bench mon → that pair is vetoed"),
    ("J6",  "Partner Clears",         ("span6", "—"),                 ["×3.0", "—", "—"],
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
            h = ROW_MIN
            body.append(f'<rect x="0" y="{y:.1f}" width="{TOTAL_W}" height="{h}" class="sec"/>')
            body.append(_hline(y))
            body.append(_text(PAD_X, y + h / 2 + 4, name, cls="tx", anchor="start",
                              fs=FS, bold=True))
            body.append(_vline(0, y, y + h))
            body.append(_vline(TOTAL_W, y, y + h))
            y += h
            continue

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

    style = """
    <style>
      .bg { fill: #ffffff; }
      .hd { fill: #f6f8fa; }
      .sec{ fill: #eaeef2; }
      .tx { fill: #1f2328; font-family: -apple-system, Segoe UI, Helvetica, Arial, sans-serif; }
      .bd { stroke: #d0d7de; stroke-width: 1; }
      @media (prefers-color-scheme: dark) {
        .bg { fill: #0d1117; }
        .hd { fill: #161b22; }
        .sec{ fill: #21262d; }
        .tx { fill: #e6edf3; }
        .bd { stroke: #30363d; }
      }
    </style>"""

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{TOTAL_W}" height="{total_h:.0f}" '
        f'viewBox="0 0 {TOTAL_W} {total_h:.0f}" font-family="sans-serif">'
        f'{style}'
        f'<rect x="0" y="0" width="{TOTAL_W}" height="{total_h:.0f}" class="bg"/>'
        + "".join(hdr) + "".join(body)
        + "</svg>\n"
    )


def main() -> None:
    OUT.write_text(build(), encoding="utf-8")
    print(f"Wrote {OUT.relative_to(OUT.parent.parent)}  ({TOTAL_W}px wide)")


if __name__ == "__main__":
    main()
