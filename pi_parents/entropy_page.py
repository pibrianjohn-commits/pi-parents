"""Stage 2 viewer: one self-contained web page of the entropy profiles.

A table puts every window size side by side; buttons switch the charts
between sizes. No scripts, so the page opens straight from disk.
"""
import html
import math

from .streams import STREAM_NAMES

COLOURS = {"parent_one": "var(--one)", "parent_two": "var(--two)",
           "pi": "var(--pi)"}
WIDTH, HEIGHT, PAD_L, PAD_B, PAD_T = 1000, 180, 48, 26, 8


def _colour(name):
    return COLOURS.get(name, "var(--muted)")


def _label(name):
    return STREAM_NAMES.get(name, name)


def _step(span):
    return 0.1 if span <= 0.8 else 0.25 if span <= 2 else 0.5


def _y(y_lo, y_hi):
    return lambda v: PAD_T + (HEIGHT - PAD_B - PAD_T) * (1 - (v - y_lo) / (y_hi - y_lo))


def _band(profile, y):
    """Min-max band per pixel column, so that every dip stays visible."""
    n = len(profile)
    cols = min(WIDTH - PAD_L, n)
    top, bottom = [], []
    for c in range(cols):
        chunk = profile[c * n // cols:max((c + 1) * n // cols, c * n // cols + 1)]
        x = PAD_L + c * (WIDTH - PAD_L) / max(cols - 1, 1)
        top.append((x, max(chunk)))
        bottom.append((x, min(chunk)))
    return " ".join(f"{x:.1f},{y(v):.1f}" for x, v in top + bottom[::-1])


def _y_grid(y_lo, y_hi, y):
    out, step = [], _step(y_hi - y_lo)
    v = math.ceil(y_lo / step - 1e-9) * step
    while v <= y_hi + 1e-9:
        out.append(f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{y(v):.1f}" '
                   f'y2="{y(v):.1f}" class="grid"/>'
                   f'<text x="{PAD_L - 6}" y="{y(v) + 4:.1f}" '
                   f'class="tick" text-anchor="end">{v:.2f}</text>')
        v = round(v + step, 6)
    return "".join(out)


def _profile_svg(name, W, profile, first_place, y_lo, y_hi, st):
    y = _y(y_lo, y_hi)
    last = first_place + len(profile) - 1
    xt = []
    for k in range(6):
        place = first_place + round(k * (len(profile) - 1) / 5)
        x = PAD_L + k * (WIDTH - PAD_L) / 5
        anchor = "start" if k == 0 else "end" if k == 5 else "middle"
        xt.append(f'<text x="{x:.1f}" y="{HEIGHT - 6}" class="tick" '
                  f'text-anchor="{anchor}">{place:,}</text>')
    ym = y(st["mean"])
    return (
        f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="{_label(name)} entropy, {W}-digit windows starting at '
        f'places {first_place:,} to {last:,}">'
        + _y_grid(y_lo, y_hi, y)
        + f'<polygon points="{_band(profile, y)}" fill="{_colour(name)}" '
          f'stroke="{_colour(name)}" stroke-width="0.6"/>'
        + f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{ym:.1f}" y2="{ym:.1f}" '
          f'class="mean"/>'
        + "".join(xt) + "</svg>")


def _histogram_svg(by_stream, lo, hi):
    """Share of windows at each entropy value.

    Small windows give only a few possible values, so those are drawn as
    one bar per value; larger windows are grouped into 60 bins.
    """
    values = sorted({round(v, 9) for p, _ in by_stream.values() for v in p})
    discrete = len(values) <= 80
    if discrete:
        keys = values
        key = lambda v: round(v, 9)
    else:
        bins = 60
        width = (hi - lo) / bins
        keys = [lo + (i + 0.5) * width for i in range(bins)]
        key = lambda v: keys[min(bins - 1, max(0, int((v - lo) / width)))]
    shares = {}
    for name, (prof, _) in by_stream.items():
        h = dict.fromkeys(keys, 0)
        for v in prof:
            h[key(v)] += 1
        shares[name] = [h[k] / len(prof) for k in keys]
    top = max(max(s) for s in shares.values())
    span = (hi - lo) or 1
    x = lambda v: PAD_L + 10 + (v - lo) / span * (WIDTH - PAD_L - 20)
    y = lambda f: PAD_T + (HEIGHT - PAD_B - PAD_T) * (1 - f / top)
    marks = []
    n = len(shares)
    for j, (name, s) in enumerate(shares.items()):
        if discrete:
            for k, f in zip(keys, s):
                if f:
                    xx = x(k) + (j - (n - 1) / 2) * 3
                    marks.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" '
                                 f'y1="{y(0):.1f}" y2="{y(f):.1f}" '
                                 f'stroke="{_colour(name)}" stroke-width="2.5"/>')
        else:
            pts = " ".join(f"{x(k):.1f},{y(f):.1f}" for k, f in zip(keys, s))
            marks.append(f'<polyline points="{pts}" fill="none" '
                         f'stroke="{_colour(name)}" stroke-width="2"/>')
    ticks, step = [], _step(hi - lo)
    v = math.ceil(lo / step - 1e-9) * step
    while v <= hi + 1e-9:
        ticks.append(f'<text x="{x(v):.1f}" y="{HEIGHT - 6}" class="tick" '
                     f'text-anchor="middle">{v:.2f}</text>')
        v = round(v + step, 6)
    return (f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
            f'aria-label="How often each entropy value occurs">'
            f'<line x1="{PAD_L}" x2="{WIDTH}" y1="{y(0):.1f}" '
            f'y2="{y(0):.1f}" class="grid"/>'
            + "".join(marks) + "".join(ticks) + "</svg>")


def _side_by_side(summary, names):
    head = "".join(
        f'<th colspan="3" class="grp"><span class="key" style="background:'
        f'{_colour(n)}"></span>{_label(n)}</th>' for n in names)
    sub = "".join("<th>average</th><th>spread</th><th>lowest</th>"
                  for _ in names)
    rows = []
    for W, ws in summary["windows"].items():
        cells = "".join(
            f"<td>{st['mean']:.4f}</td><td>{st['stdev']:.4f}</td>"
            f"<td>{st['minimum']:.4f}</td>" for st in ws["streams"].values())
        rows.append(f"<tr><th>{W}</th><td>{ws['most_possible']:.4f}</td>"
                    f"{cells}</tr>")
    return (f'<div class="scroll"><table class="num"><tr><th rowspan="2">window'
            f'</th><th rowspan="2">most<br>possible</th>{head}</tr>'
            f'<tr>{sub}</tr>{"".join(rows)}</table></div>')


def _panel(W, by_stream, ws):
    lo = min(min(p) for p, _ in by_stream.values())
    hi = max(max(p) for p, _ in by_stream.values())
    step = _step(hi - lo)
    y_lo = math.floor(lo / step) * step
    y_hi = max(ws["most_possible"], hi)
    parts = []
    for name, (prof, first_place) in by_stream.items():
        st = ws["streams"][name]
        rows = "".join(
            f"<tr><td>{w['start_place']:,}</td><td>{w['entropy']:.4f}</td>"
            f"<td class='digits'>{html.escape(w['digits'])}</td></tr>"
            for w in st["lowest_windows"])
        parts.append(f"""
  <h2><span class="key" style="background:{_colour(name)}"></span>{_label(name)}</h2>
  <p class="stats">average {st['mean']:.4f} bits &middot; spread (sd) {st['stdev']:.4f}
     &middot; lowest {st['minimum']:.4f} &middot; highest {st['maximum']:.4f}</p>
  {_profile_svg(name, W, prof, first_place, y_lo, y_hi, st)}
  <details><summary>Lowest-entropy windows (none overlapping)</summary>
  <table><tr><th>starts at place</th><th>entropy</th><th>digits</th></tr>{rows}</table>
  </details>""")
    legend = " ".join(
        f'<span class="legend"><span class="key" style="background:{_colour(n)}">'
        f'</span>{_label(n)}</span>' for n in by_stream)
    return f"""<section class="panel" id="panel{W}">
  <p class="note">{W}-digit windows. The most a {W}-digit window can reach is
    {ws['most_possible']:.4f} bits, the top edge of each chart.</p>
  {''.join(parts)}
  <h2>All together: how often each entropy value occurs</h2>
  <p class="note">Height is the share of windows with that entropy.</p>
  <p>{legend}</p>
  {_histogram_svg(by_stream, lo, y_hi)}
</section>"""


def write(path, profiles, summary):
    s = summary["settings"]
    windows = list(profiles)
    names = list(profiles[windows[0]])
    lead = ("leading whole-number digit included" if s["include_leading_digit"]
            else "decimals only")
    radios = "".join(
        f'<input type="radio" name="w" id="w{W}"{" checked" if i == 0 else ""}>'
        for i, W in enumerate(windows))
    labels = "".join(f'<label for="w{W}">{W} digits</label>' for W in windows)
    show = "\n".join(
        f"#w{W}:checked ~ .tabs label[for=w{W}] {{ background:var(--fg); "
        f"color:var(--bg); }}\n#w{W}:checked ~ #panel{W} {{ display:block; }}"
        for W in windows)
    panels = "".join(_panel(W, profiles[W], summary["windows"][str(W)])
                     for W in windows)
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
  text-align:left; vertical-align:top; font-weight:normal; }}
th {{ color:var(--muted); }}
table.num td {{ font-variant-numeric:tabular-nums; }}
table.num th.grp {{ color:var(--fg); padding-top:10px; }}
.scroll {{ overflow-x:auto; }}
.digits {{ font-family:ui-monospace, Menlo, monospace; word-break:break-all; }}
input[name=w] {{ position:absolute; opacity:0; pointer-events:none; }}
.tabs {{ display:flex; flex-wrap:wrap; gap:6px; margin:28px 0 4px; }}
.tabs label {{ border:1px solid var(--line); border-radius:4px; padding:4px 12px;
  cursor:pointer; font:14px system-ui, sans-serif; }}
.panel {{ display:none; }}
{show}
</style></head><body>
<h1>Entropy profile</h1>
<p class="sub">Windows of {", ".join(map(str, windows))} digits, each sliding one
  digit at a time &middot; {s['decimal_places']:,} decimal places &middot; {lead}</p>
<p class="note">Higher means the digits in the window are more evenly mixed.
  Dips are stretches where a few digits dominate. In the charts the shaded band
  shows the lowest and highest value in each slice of the stream, the dashed
  line is the average, and along the bottom is the decimal place where each
  window starts.</p>
<h2>Every window size side by side</h2>
<p class="note">Entropy in bits. "Most possible" is the highest a window of
  that size can reach. Spread is the standard deviation.</p>
{_side_by_side(summary, names)}
{radios}
<div class="tabs">{labels}</div>
{panels}
</body></html>
""")
