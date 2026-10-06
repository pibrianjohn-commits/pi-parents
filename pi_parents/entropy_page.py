"""Stage 2 viewer: one self-contained web page of the entropy profiles."""
import html
import math

from .streams import STREAM_NAMES

COLOURS = {"parent_one": "var(--one)", "parent_two": "var(--two)",
           "pi": "var(--pi)"}
WIDTH, HEIGHT, PAD_L, PAD_B, PAD_T = 1000, 180, 48, 26, 8


def _band(profile, y_lo, y_hi):
    """Min-max band per pixel column, so that every dip stays visible."""
    n = len(profile)
    cols = min(WIDTH - PAD_L, n)
    top, bottom = [], []
    for c in range(cols):
        chunk = profile[c * n // cols:max((c + 1) * n // cols, c * n // cols + 1)]
        x = PAD_L + c * (WIDTH - PAD_L) / max(cols - 1, 1)
        top.append((x, max(chunk)))
        bottom.append((x, min(chunk)))
    y = lambda v: PAD_T + (HEIGHT - PAD_B - PAD_T) * (1 - (v - y_lo) / (y_hi - y_lo))
    pts = top + bottom[::-1]
    return " ".join(f"{x:.1f},{y(v):.1f}" for x, v in pts), y


def _profile_svg(name, profile, first_place, y_lo, y_hi, st):
    pts, y = _band(profile, y_lo, y_hi)
    last = first_place + len(profile) - 1
    grid = []
    v = y_lo
    while v <= y_hi + 1e-9:
        grid.append(f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{y(v):.1f}" '
                    f'y2="{y(v):.1f}" class="grid"/>'
                    f'<text x="{PAD_L - 6}" y="{y(v) + 4:.1f}" '
                    f'class="tick" text-anchor="end">{v:.1f}</text>')
        v = round(v + 0.1, 1)
    ym = y(st["mean"])
    xt = []
    for k in range(6):
        place = first_place + round(k * (len(profile) - 1) / 5)
        x = PAD_L + k * (WIDTH - PAD_L) / 5
        anchor = "start" if k == 0 else "end" if k == 5 else "middle"
        xt.append(f'<text x="{x:.1f}" y="{HEIGHT - 6}" class="tick" '
                  f'text-anchor="{anchor}">{place:,}</text>')
    return (
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{STREAM_NAMES[name]} entropy, windows starting at '
        f'places {first_place:,} to {last:,}">'
        + "".join(grid)
        + f'<polygon points="{pts}" fill="{COLOURS[name]}" '
          f'stroke="{COLOURS[name]}" stroke-width="0.6"/>'
        + f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{ym:.1f}" y2="{ym:.1f}" '
          f'class="mean"/>'
        + "".join(xt) + "</svg>")


def _histogram_svg(profiles, lo, hi, bins=60):
    w = (hi - lo) / bins
    hists = {}
    for name, (prof, _) in profiles.items():
        h = [0] * bins
        for v in prof:
            h[min(bins - 1, max(0, int((v - lo) / w)))] += 1
        hists[name] = [c / len(prof) for c in h]
    top = max(max(h) for h in hists.values())
    x = lambda v: PAD_L + (v - lo) / (hi - lo) * (WIDTH - PAD_L)
    y = lambda f: PAD_T + (HEIGHT - PAD_B - PAD_T) * (1 - f / top)
    lines = []
    for name, h in hists.items():
        pts = " ".join(f"{x(lo + (i + 0.5) * w):.1f},{y(f):.1f}"
                       for i, f in enumerate(h))
        lines.append(f'<polyline points="{pts}" fill="none" '
                     f'stroke="{COLOURS[name]}" stroke-width="2"/>')
    ticks = []
    v = math.ceil(lo * 4) / 4
    while v <= hi:
        ticks.append(f'<text x="{x(v):.1f}" y="{HEIGHT - 6}" class="tick" '
                     f'text-anchor="middle">{v:.2f}</text>')
        v += 0.25
    return (f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
            f'aria-label="How often each entropy value occurs">'
            f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{HEIGHT - PAD_B}" '
            f'y2="{HEIGHT - PAD_B}" class="grid"/>'
            + "".join(lines) + "".join(ticks) + "</svg>")


def write(path, profiles, summary):
    s = summary["settings"]
    lo = min(min(p) for p, _ in profiles.values())
    hi = max(max(p) for p, _ in profiles.values())
    y_lo, y_hi = math.floor(lo * 10) / 10, math.ceil(hi * 10) / 10

    sections = []
    for name, (prof, first_place) in profiles.items():
        st = summary["streams"][name]
        rows = "".join(
            f"<tr><td>{w['start_place']:,}</td><td>{w['entropy']:.4f}</td>"
            f"<td class='digits'>{html.escape(w['digits'])}</td></tr>"
            for w in st["lowest_windows"])
        sections.append(f"""
<section>
  <h2><span class="key" style="background:{COLOURS[name]}"></span>{STREAM_NAMES[name]}</h2>
  <p class="stats">average {st['mean']:.4f} bits &middot; spread (sd) {st['stdev']:.4f}
     &middot; lowest {st['minimum']:.4f} &middot; highest {st['maximum']:.4f}</p>
  {_profile_svg(name, prof, first_place, y_lo, y_hi, st)}
  <details><summary>Lowest-entropy windows (none overlapping)</summary>
  <table><tr><th>starts at place</th><th>entropy</th><th>digits</th></tr>{rows}</table>
  </details>
</section>""")

    lead = ("leading whole-number digit included" if s["include_leading_digit"]
            else "decimals only")
    legend = " ".join(
        f'<span class="legend"><span class="key" style="background:{COLOURS[n]}">'
        f'</span>{STREAM_NAMES[n]}</span>' for n in profiles)
    path.write_text(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Entropy profile</title>
<style>
:root {{ --bg:#fbfaf7; --fg:#22201c; --muted:#6b665d; --line:#dedad2;
  --one:#b5562b; --two:#2f6f9f; --pi:#6c7a3a; }}
@media (prefers-color-scheme: dark) {{ :root {{ --bg:#1b1a18; --fg:#ece8e0;
  --muted:#a39d92; --line:#3a3732; --one:#e08a5c; --two:#6fa8d6; --pi:#a8b86a; }} }}
body {{ background:var(--bg); color:var(--fg); margin:0 auto; max-width:1040px;
  padding:24px 16px 48px; font:16px/1.5 Georgia, "Times New Roman", serif; }}
h1 {{ font-weight:normal; margin:0 0 4px; }}
h2 {{ font-weight:normal; font-size:1.2rem; margin:28px 0 2px; }}
.sub, .stats, .note {{ color:var(--muted); margin:0 0 8px; }}
svg {{ width:100%; height:auto; display:block; }}
svg polygon {{ fill-opacity:.35; }}
.grid {{ stroke:var(--line); stroke-width:1; }}
.mean {{ stroke:var(--fg); stroke-width:1; stroke-dasharray:4 4; opacity:.6; }}
.tick {{ fill:var(--muted); font:12px system-ui, sans-serif; }}
.key {{ display:inline-block; width:12px; height:12px; border-radius:2px;
  margin-right:8px; vertical-align:-1px; }}
.legend {{ margin-right:18px; color:var(--muted); }}
details {{ margin-top:6px; }} summary {{ cursor:pointer; color:var(--muted); }}
table {{ border-collapse:collapse; font-size:14px; margin-top:6px; }}
td, th {{ border-bottom:1px solid var(--line); padding:4px 10px 4px 0;
  text-align:left; vertical-align:top; }}
.digits {{ font-family:ui-monospace, Menlo, monospace; word-break:break-all; }}
</style></head><body>
<h1>Entropy profile</h1>
<p class="sub">Window {s['entropy_window']} digits, sliding one digit at a time
  &middot; {s['decimal_places']:,} decimal places &middot; {lead}</p>
<p class="note">Higher means the digits in the window are more evenly mixed
  (the most possible is 3.32 bits). Dips are stretches where a few digits
  dominate. The shaded band shows the lowest and highest value in each slice
  of the stream; the dashed line is the average. Along the bottom is the
  decimal place where each window starts.</p>
{''.join(sections)}
<section>
  <h2>All three together: how often each entropy value occurs</h2>
  <p class="note">Height is the share of windows with that entropy.</p>
  <p>{legend}</p>
  {_histogram_svg(profiles, lo, hi)}
</section>
</body></html>
""")
