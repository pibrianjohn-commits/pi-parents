"""Does Parent One's low-entropy lean hold at 100,000 places?

The Stage 4 measure, unchanged: the stack of 2-30-digit primes (how many
pass through each digit) inside the lowest-entropy windows, against the
rest of the stream, each divided by what prime density predicts for those
same digits:

    lean = (found / density, low-entropy digits)
           / (found / density, all other digits)

1.000 means no lean. Low-entropy digits: those inside the lowest-entropy
windows, taking as many of the lowest values as stay within 5% of windows.

At 100,000 places the stream is also cut into ten blocks of 10,000. Each
block's lean is worked out with the whole stream's low-entropy cut-off;
the spread of the ten shows how much the lean moves by chance within one
stream, with no random streams needed.
"""
import csv
import json
import math
import statistics

import numpy as np

from . import chance, primes, streams
from .structure import RESULTS_DIR, low_entropy_digits, stack

WINDOWS = (15, 20, 30, 50)
BAND = (2, 30)
BLOCKS = 10


def stacks(digits, runs):
    """Found and predicted stack of BAND primes at every digit."""
    a, b = BAND
    n = len(digits)
    obs = np.zeros((n, b))
    for s, L in runs:
        if a <= L <= b:
            obs[s, L - 1] = 1.0
    exp = chance.run_chance(digits, b)
    exp[:, :a - 1] = 0.0
    return stack(obs), stack(exp)


def lean(o, e, low):
    return float((o[low].sum() / e[low].sum()) / (o[~low].sum() / e[~low].sum()))


def load_runs(tag, pass_name, names):
    runs = {n: [] for n in names}
    path = primes.out_dir(tag) / f"primes_pass_{pass_name}.csv"
    with open(path) as f:
        for row in csv.DictReader(f):
            if row["stream"] in runs:
                runs[row["stream"]].append(
                    (int(row["start_place"]) - 1, int(row["length"])))
    return runs


def analyse(D, tag, pass_name, blocks=1):
    stream_set = {n: d for n, (d, _) in streams.load_streams(D).items()}
    runs = load_runs(tag, pass_name, stream_set)
    out = {}
    for name, digits in stream_set.items():
        o, e = stacks(digits, runs[name])
        res = {}
        for W in WINDOWS:
            low, cut, share = low_entropy_digits(digits, W)
            row = dict(lean=lean(o, e, low), digits_low=float(low.mean()),
                       cutoff_bits=cut,
                       low_found=float(o[low].mean()), low_density=float(e[low].mean()),
                       rest_found=float(o[~low].mean()), rest_density=float(e[~low].mean()))
            if blocks > 1:
                size = len(digits) // blocks
                per = []
                for k in range(blocks):
                    sl = slice(k * size, (k + 1) * size)
                    per.append(lean(o[sl], e[sl], low[sl]))
                sd = statistics.stdev(per)
                row.update(blocks=per, block_mean=statistics.fmean(per),
                           block_sd=sd, blocks_above_1=int(sum(x > 1 for x in per)),
                           standard_error=sd / math.sqrt(blocks))
            res[W] = row
        out[name] = res
    return out


def run():
    small = analyse(10_000, None, "A", 1)
    big = analyse(100_000, "D100000", "A30", BLOCKS)
    summary = dict(
        settings=dict(windows=list(WINDOWS), band=list(BAND), blocks=BLOCKS,
                      low_entropy="lowest values, at most 5% of windows"),
        D10000=small, D100000=big)
    out_dir = RESULTS_DIR / "D100000"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "lean_summary.json").write_text(json.dumps(summary, indent=1) + "\n")
    return summary


def report(summary):
    names = {"parent_one": "Parent One", "parent_two": "Parent Two", "pi": "Pi"}
    lines = ["Lean = (found / density in low-entropy digits) / (found / density",
             "elsewhere), stack of 2-30-digit primes. 1.000 = no lean.", ""]
    head = f"{'':<12}{'window':>7}{'10,000':>9}{'100,000':>9}   {'blocks: mean  sd   above 1':<28}{'(100k - 1) / s.e.':>18}"
    lines.append(head)
    for n in names:
        for W in WINDOWS:
            a = summary["D10000"][n][W]
            b = summary["D100000"][n][W]
            z = (b["lean"] - 1) / b["standard_error"]
            lines.append(f"{names[n]:<12}{W:>7}{a['lean']:>9.3f}{b['lean']:>9.3f}   "
                         f"{b['block_mean']:>11.3f}{b['block_sd']:>6.3f}{b['blocks_above_1']:>6}/10"
                         f"{z:>19.1f}")
        lines.append("")
    text = "\n".join(lines)
    (RESULTS_DIR / "D100000" / "lean_report.txt").write_text(text + "\n")
    return text


if __name__ == "__main__":
    print(report(run()))
