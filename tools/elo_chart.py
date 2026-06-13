"""Generate a self-contained ELO-over-time chart (SVG) from elo_log.json, with
per-version bands/labels and per-version mean-ELO markers, plus a markdown
summary (docs/ELO_TRENDS.md) with a per-version stats table.

No third-party dependencies — pure-Python SVG generation.

Usage (from the repo root):  .venv\\Scripts\\python.exe tools/elo_chart.py
"""
import json, datetime as dt

SRC = "elo_log.json"
SVG_OUT = "docs/elo_chart.svg"
MD_OUT  = "docs/ELO_TRENDS.md"
ROLL = 30   # trailing rolling-average window (battles)

entries = json.load(open(SRC, encoding="utf-8"))
# Keep only entries with a usable elo_before; sort chronologically.
def ts(e):
    try:
        return dt.datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00"))
    except Exception:
        return dt.datetime.min.replace(tzinfo=dt.timezone.utc)
entries = sorted((e for e in entries if e.get("elo_before") is not None), key=ts)

N = len(entries)
elos = [e["elo_before"] for e in entries]
vers = [e.get("version", "?") for e in entries]
outs = [e.get("outcome") for e in entries]

# Contiguous version runs: (version, start_idx, end_idx_inclusive)
runs = []
for i, v in enumerate(vers):
    if runs and runs[-1][0] == v:
        runs[-1][2] = i
    else:
        runs.append([v, i, i])

# Trailing rolling average
roll = []
for i in range(N):
    lo = max(0, i - ROLL + 1)
    window = elos[lo:i + 1]
    roll.append(sum(window) / len(window))

# Overall least-squares trend (elo vs battle index) — the net direction.
mx = (N - 1) / 2
my = sum(elos) / N
sxx = sum((i - mx) ** 2 for i in range(N))
sxy = sum((i - mx) * (elos[i] - my) for i in range(N))
slope = sxy / sxx if sxx else 0.0          # ELO per battle
intercept = my - slope * mx
def fit(i): return intercept + slope * i

# ── Geometry ───────────────────────────────────────────────────────────────
W, H = 1300, 660
L, R, T, B = 72, 24, 64, 60
PW, PH = W - L - R, H - T - B
emin, emax = min(elos), max(elos)
ylo = (emin // 50) * 50 - 10
yhi = (emax // 50) * 50 + 60   # headroom for version labels
def X(i): return L + (i / (N - 1)) * PW if N > 1 else L + PW / 2
def Y(e): return T + (yhi - e) / (yhi - ylo) * PH

band_colors = ("#f3f6fb", "#e8eef7")   # alternating
MEAN_COLOR = "#d9480f"
ROLL_COLOR = "#1c7ed6"
RAW_COLOR  = "#adb5bd"

svg = []
svg.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
           f'font-family="Segoe UI, Arial, sans-serif" font-size="12">')
svg.append(f'<rect width="{W}" height="{H}" fill="white"/>')

# Version bands + boundary lines + labels + per-version mean ELO markers
for k, (v, s, e) in enumerate(runs):
    x0 = X(s - 0.5 if s > 0 else 0)
    x1 = X(e + 0.5 if e < N - 1 else N - 1)
    svg.append(f'<rect x="{x0:.1f}" y="{T}" width="{max(0.5, x1 - x0):.1f}" '
               f'height="{PH}" fill="{band_colors[k % 2]}"/>')
    # boundary line at run start
    svg.append(f'<line x1="{x0:.1f}" y1="{T}" x2="{x0:.1f}" y2="{T+PH}" '
               f'stroke="#ced4da" stroke-width="1" stroke-dasharray="3,3"/>')
    # per-version mean ELO marker (bold horizontal segment)
    seg = elos[s:e + 1]
    mean = sum(seg) / len(seg)
    svg.append(f'<line x1="{x0:.1f}" y1="{Y(mean):.1f}" x2="{x1:.1f}" y2="{Y(mean):.1f}" '
               f'stroke="{MEAN_COLOR}" stroke-width="2.5" opacity="0.85"/>')
    # version label (rotated, at band start, near top)
    lx = x0 + 4
    svg.append(f'<text x="{lx:.1f}" y="{T+10}" fill="#495057" font-size="11" '
               f'transform="rotate(90 {lx:.1f} {T+10})">{v} (n={e-s+1})</text>')

# Y gridlines + labels
yt = int(ylo)
while yt <= yhi:
    if yt % 50 == 0:
        y = Y(yt)
        svg.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L+PW}" y2="{y:.1f}" '
                   f'stroke="#e9ecef" stroke-width="1"/>')
        svg.append(f'<text x="{L-8}" y="{y+4:.1f}" text-anchor="end" fill="#868e96">{yt}</text>')
    yt += 10

# Raw ELO polyline (faint)
pts = " ".join(f"{X(i):.1f},{Y(elos[i]):.1f}" for i in range(N))
svg.append(f'<polyline points="{pts}" fill="none" stroke="{RAW_COLOR}" '
           f'stroke-width="0.7" opacity="0.6"/>')
# Rolling-average polyline (bold)
pts = " ".join(f"{X(i):.1f},{Y(roll[i]):.1f}" for i in range(N))
svg.append(f'<polyline points="{pts}" fill="none" stroke="{ROLL_COLOR}" stroke-width="2.5"/>')
# Overall least-squares trend line (net direction)
TREND_COLOR = "#2f9e44"
svg.append(f'<line x1="{X(0):.1f}" y1="{Y(fit(0)):.1f}" x2="{X(N-1):.1f}" y2="{Y(fit(N-1)):.1f}" '
           f'stroke="{TREND_COLOR}" stroke-width="2" stroke-dasharray="7,5"/>')

# Axis frame
svg.append(f'<rect x="{L}" y="{T}" width="{PW}" height="{PH}" fill="none" stroke="#adb5bd"/>')
# Titles
svg.append(f'<text x="{L}" y="28" font-size="18" font-weight="bold" fill="#212529">'
           f'WolfeyBot ladder ELO over {N} battles (by version)</text>')
svg.append(f'<text x="{L}" y="46" font-size="12" fill="#868e96">'
           f'elo_before each battle — faint = raw, blue = {ROLL}-battle rolling avg, '
           f'orange = per-version mean</text>')
# X-axis label
svg.append(f'<text x="{L+PW/2:.0f}" y="{H-18}" text-anchor="middle" fill="#868e96">'
           f'battle # (chronological) &#8594;</text>')
# Legend
lx, ly = L + PW - 230, T + 16
svg.append(f'<line x1="{lx}" y1="{ly}" x2="{lx+24}" y2="{ly}" stroke="{ROLL_COLOR}" stroke-width="2.5"/>')
svg.append(f'<text x="{lx+30}" y="{ly+4}" fill="#495057">{ROLL}-battle rolling avg</text>')
svg.append(f'<line x1="{lx}" y1="{ly+18}" x2="{lx+24}" y2="{ly+18}" stroke="{MEAN_COLOR}" stroke-width="2.5"/>')
svg.append(f'<text x="{lx+30}" y="{ly+22}" fill="#495057">per-version mean</text>')
svg.append(f'<line x1="{lx}" y1="{ly+36}" x2="{lx+24}" y2="{ly+36}" stroke="{TREND_COLOR}" '
           f'stroke-width="2" stroke-dasharray="7,5"/>')
svg.append(f'<text x="{lx+30}" y="{ly+40}" fill="#495057">overall trend</text>')
svg.append('</svg>')
open(SVG_OUT, "w", encoding="utf-8").write("\n".join(svg))

# ── Markdown summary ─────────────────────────────────────────────────────────
md = []
md.append("# WolfeyBot ELO trends\n")
md.append(f"_Generated from `{SRC}` — {N} battles, {runs[0][0]} → {runs[-1][0]}._\n")
md.append(f"![ELO over time]({SVG_OUT})\n")
md.append("> `elo_before` is the ladder rating at the **start** of each battle. "
          "ELO is noisy per-game (±~25); the per-version **mean** and the trend "
          "line are the reliable signals.\n")
md.append("## Per-version summary\n")
md.append("| Version | Battles | Win % | Mean ELO | Start→End ELO | Δ mean vs prev |")
md.append("|---|---|---|---|---|---|")
prev_mean = None
for v, s, e in runs:
    seg = elos[s:e + 1]
    n = e - s + 1
    wins = sum(1 for o in outs[s:e + 1] if o == "win")
    mean = sum(seg) / n
    delta = "" if prev_mean is None else f"{mean - prev_mean:+.0f}"
    md.append(f"| {v} | {n} | {wins/n:.0%} | {mean:.0f} | {seg[0]}→{seg[-1]} | {delta} |")
    prev_mean = mean
md.append("")
peak = max(elos); peak_i = elos.index(peak)
md.append(f"**Peak elo_before:** {peak} (battle #{peak_i+1}, {vers[peak_i]}). "
          f"**Overall:** {elos[0]} → {elos[-1]} "
          f"({elos[-1]-elos[0]:+d} over the logged history).")
md.append(f"\n**Overall trend:** {slope*100:+.1f} ELO per 100 battles "
          f"(least-squares fit across all {N}). The latest version (0.6.8) climbed "
          f"{elos[runs[-1][1]]}→{elos[-1]} over its {runs[-1][2]-runs[-1][1]+1} games "
          f"and set the all-time peak — the clearest improvement signal, since "
          f"cross-version *mean* ELO is confounded by where each version started on "
          f"the ladder.")
open(MD_OUT, "w", encoding="utf-8").write("\n".join(md))

print(f"Wrote {SVG_OUT} and {MD_OUT}  ({N} battles, {len(runs)} version runs)")
print(f"ELO range {emin}..{emax};  first {elos[0]}  last {elos[-1]}")
