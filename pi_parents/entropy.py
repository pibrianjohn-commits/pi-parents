"""Stage 2: Shannon entropy profile along a digit stream.

A window of W digits slides along the stream one digit at a time. For each
window position the entropy, in bits, is

    H = -sum over digits d of p(d) * log2 p(d),   p(d) = count(d) / W

H is 0 when the window is one repeated digit, and at most log2(10) = 3.32
bits when all ten digits are equally common.
"""
import csv
import json
import math
import statistics
import sys
from pathlib import Path

from . import settings, streams

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "stage2"


def window_entropy(window):
    """Entropy of one window, computed directly (used to check the profile)."""
    W = len(window)
    return -sum(c / W * math.log2(c / W)
                for c in (window.count(d) for d in "0123456789") if c)


def entropy_profile(digits, W):
    """Entropy of every W-digit window, by window start index."""
    if not 0 < W <= len(digits):
        raise ValueError(f"window {W} does not fit a {len(digits)}-digit stream")
    # H = log2 W - (1/W) * sum of c*log2 c over the digit counts c.
    clogc = [0.0] + [c * math.log2(c) for c in range(1, W + 1)]
    vals = [ord(ch) - 48 for ch in digits]
    counts = [0] * 10
    for v in vals[:W]:
        counts[v] += 1
    s = sum(clogc[c] for c in counts)
    logW = math.log2(W)
    out = [logW - s / W]
    for i in range(W, len(vals)):
        old, new = vals[i - W], vals[i]
        if old != new:
            s -= clogc[counts[old]] + clogc[counts[new]]
            counts[old] -= 1
            counts[new] += 1
            s += clogc[counts[old]] + clogc[counts[new]]
        out.append(max(0.0, logW - s / W))
    return out


def summarise(profile, digits, first_place, W, listed):
    order = sorted(range(len(profile)), key=lambda i: (profile[i], i))
    lowest, taken = [], []
    for i in order:                    # lowest windows that don't overlap
        if all(abs(i - j) >= W for j in taken):
            taken.append(i)
            lowest.append(dict(start_place=first_place + i,
                               entropy=round(profile[i], 6),
                               digits=digits[i:i + W]))
            if len(lowest) == listed:
                break
    return dict(
        windows=len(profile),
        mean=statistics.fmean(profile),
        stdev=statistics.pstdev(profile),
        minimum=min(profile),
        maximum=max(profile),
        lowest_windows=lowest,
    )


def max_entropy(W):
    """The most entropy a W-digit window can have: digits spread as evenly
    as possible over all ten."""
    q, r = divmod(W, 10)
    counts = [q + 1] * r + [q] * (10 - r)
    return -sum(c / W * math.log2(c / W) for c in counts if c)


def run(windows=None, include_leading_digit=None, D=None, stream_set=None,
        write_page=False):
    """Entropy profiles at every window size, for every stream.

    stream_set maps a stream name to (digits, first place); by default it
    is Parent One, Parent Two and pi.
    """
    windows = settings.ENTROPY_WINDOWS if windows is None else tuple(windows)
    if include_leading_digit is None:
        include_leading_digit = settings.INCLUDE_LEADING_DIGIT
    D = settings.DECIMAL_PLACES if D is None else D
    if stream_set is None:
        stream_set = streams.load_streams(D, include_leading_digit)
    lead = "with_lead" if include_leading_digit else "decimals_only"
    out_dir = RESULTS_DIR / f"D{D}_{lead}"
    out_dir.mkdir(parents=True, exist_ok=True)

    run_settings = dict(decimal_places=D, entropy_windows=list(windows),
                        include_leading_digit=include_leading_digit)
    summary = dict(settings=run_settings, windows={})
    profiles = {}
    for W in windows:
        profiles[W] = {}
        summary["windows"][str(W)] = dict(most_possible=max_entropy(W),
                                          streams={})
        for name, (digits, first_place) in stream_set.items():
            prof = entropy_profile(digits, W)
            profiles[W][name] = (prof, first_place)
            summary["windows"][str(W)]["streams"][name] = summarise(
                prof, digits, first_place, W, settings.LOWEST_WINDOWS_LISTED)
            with open(out_dir / f"entropy_W{W}_{name}.csv", "w",
                      newline="") as f:
                w = csv.writer(f)
                w.writerow(["window_start_place", "entropy_bits"])
                w.writerows((first_place + i, f"{h:.6f}")
                            for i, h in enumerate(prof))

    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    if write_page:                   # Brian asked for no new pages
        from . import entropy_page
        entropy_page.write(out_dir / "entropy.html", profiles, summary)
    return out_dir, summary


def report(summary):
    s = summary["settings"]
    names = list(next(iter(summary["windows"].values()))["streams"])
    lines = [f"{'leading digit included' if s['include_leading_digit'] else 'decimals only'}, "
             f"{s['decimal_places']:,} places; average / lowest entropy in bits",
             "window  most  " + "".join(
                 f"{streams.STREAM_NAMES.get(n, n):>20}" for n in names)]
    for W, ws in summary["windows"].items():
        lines.append(f"{W:>6}  {ws['most_possible']:.3f}" + "".join(
            f"{st['mean']:>12.4f} / {st['minimum']:.3f}"
            for st in ws["streams"].values()))
    return "\n".join(lines)


if __name__ == "__main__":
    windows = [int(a) for a in sys.argv[1:]] or None
    out_dir, summary = run(windows)
    print(report(summary))
    print("saved", out_dir.relative_to(RESULTS_DIR.parent.parent))
