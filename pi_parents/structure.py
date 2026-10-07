"""Stage 4: towers and structure among the saved primes (Passes A and B).

Words used, for a prime run P from place s up to (not including) e:
  prefix  a shorter prime run with the same first digit as P
  suffix  a shorter prime run with the same last digit as P
  nested  a prime run strictly inside P, touching neither end
  inside  any of the three (P contains it)
  depth   the longest chain of primes, each inside the one before
  stack   how many prime runs pass through a digit
  overlap two prime runs that share digits, neither inside the other
  giant   a prime run of at least GIANT_MIN digits
  bridge  for a giant whose longest prime prefix and longest prime suffix
          don't meet: a prime inside the giant that spans the gap
  cover   a prime that contains two giants that overlap each other

Most counts are worked out twice: from the primes actually found, and as
the number prime density predicts, treating every run as prime with its
Stage 3 chance, independently. Both use the same array arithmetic: an
array w[start, length - 1] holding 1 for a prime and 0 otherwise, or the
run's chance of being prime.
"""
import bisect
import csv
import gzip
import json
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from . import chance, entropy, primes, settings, streams

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "stage4"
LMAX = 1000
GIANT_MIN = 101          # Pass B primes; Brian's named giants are longer
LOW_SHARE = 0.05         # low-entropy windows: at most this share of windows
STACK_BANDS = ((2, 30), (1, 100), (101, 1000), (1, 1000))


# ------------------------------------------------------------ the arrays

def to_end(w):
    """Re-index w[start, L - 1] by end place: out[end, L - 1]."""
    n, Lmax = w.shape
    out = np.zeros((n + 1, Lmax), dtype=w.dtype)
    for L in range(1, Lmax + 1):
        out[L:, L - 1] = w[:n + 1 - L, L - 1]
    return out


def to_start(x_end, n):
    Lmax = x_end.shape[1]
    out = np.zeros((n, Lmax), dtype=x_end.dtype)
    for L in range(1, Lmax + 1):
        out[:n + 1 - L, L - 1] = x_end[L:, L - 1]
    return out


def _excl_cumsum(a):
    out = np.zeros_like(a)
    np.cumsum(a[:, :-1], axis=1, out=out[:, 1:])
    return out


def _nested_sum(a_end, n):
    """For each run (start s, length L): the sum of a over runs strictly
    inside it. a_end is indexed by end place."""
    Lmax = a_end.shape[1]
    R = np.cumsum(a_end, axis=1)          # R[e, m-1]: lengths <= m ending at e
    T = np.zeros((n, Lmax))
    for j in range(2, Lmax):              # j = inner end - outer start
        T[:n - j + 1, j] = R[j:n + 1, j - 2]
    return np.cumsum(T, axis=1)


def _logs(w):
    with np.errstate(divide="ignore"):
        return np.log1p(-w)


def _any(log_sum):
    return 1.0 - np.exp(log_sum)


def tower_counts(w):
    """Prefix, suffix and nested counts for weights w (0/1 or chances).

    Returns per-run arrays (number inside, chance of at least one) and
    totals: pairs, and primes with at least one of each kind.
    """
    n = w.shape[0]
    lw, we = _logs(w), to_end(w)
    lwe = _logs(we)
    per = dict(
        prefix=_excl_cumsum(w),
        suffix=to_start(_excl_cumsum(we), n),
        nested=_nested_sum(we, n),
    )
    any_ = dict(
        prefix=_any(_excl_cumsum(lw)),
        suffix=_any(to_start(_excl_cumsum(lwe), n)),
        nested=_any(_nested_sum(lwe, n)),
    )
    totals = {}
    for k in per:
        totals[f"{k}_pairs"] = float((w * per[k]).sum())
        totals[f"with_{k}"] = float((w * any_[k]).sum())
    totals["with_prefix_and_suffix"] = float(
        (w * any_["prefix"] * any_["suffix"]).sum())
    return per, any_, totals


def by_band(w, per_run, bands):
    """Sum of w * per_run over outer runs in each length band."""
    return {f"{a}-{b}": float((w[:, a - 1:b] * per_run[:, a - 1:b]).sum())
            for a, b in bands}


def overlap_counts(w):
    """Pairs of runs that share k digits, neither inside the other.

    Run A ends at e and is longer than k; run B starts at e - k and is
    longer than k. Returns counts for k = 1 .. Lmax - 1.
    """
    n, Lmax = w.shape
    we = to_end(w)
    tot_s, tot_e = w.sum(axis=1), we.sum(axis=1)
    cum_s, cum_e = np.cumsum(w, axis=1), np.cumsum(we, axis=1)
    out = np.zeros(Lmax)
    for k in range(1, Lmax):
        right_s = tot_s - cum_s[:, k - 1]          # starts at s, longer than k
        right_e = tot_e - cum_e[:, k - 1]          # ends at e, longer than k
        out[k] = float(right_e[k:n + 1] @ right_s[:n + 1 - k])
    return out


def stack(w):
    """How many runs (or expected runs) pass through each digit."""
    n = w.shape[0]
    diff = np.zeros(n + 1)
    diff[:n] += w.sum(axis=1)
    diff -= to_end(w).sum(axis=1)
    return np.cumsum(diff)[:n]


def stack_by_band(w, bands=STACK_BANDS):
    out = {}
    for a, b in bands:
        part = np.zeros_like(w)
        part[:, a - 1:b] = w[:, a - 1:b]
        out[f"{a}-{b}"] = stack(part)
    return out


def depth(prime_mask):
    """Nesting depth of every prime: 1 + the deepest prime inside it."""
    n, Lmax = prime_mask.shape
    d = np.zeros((n, Lmax), dtype=np.int32)
    best = np.zeros(n + 1, dtype=np.int32)   # deepest within [a, a + l - 1)
    for L in range(1, Lmax + 1):
        m = n - L + 1
        if m <= 0:
            break
        inner = np.maximum(best[:m], best[1:m + 1])
        here = np.where(prime_mask[:m, L - 1], inner + 1, 0)
        d[:m, L - 1] = here
        best = np.maximum(here, inner)
    return d


# ------------------------------------------------- lists from the primes

class Primes:
    """The primes of one stream, with lookups by start and by end."""

    def __init__(self, runs, n, Lmax=LMAX):
        self.n = n
        self.runs = sorted(runs)
        self.by_start = defaultdict(list)
        self.by_end = defaultdict(list)
        for s, L in self.runs:
            self.by_start[s].append(L)
            self.by_end[s + L].append(L)
        for v in self.by_start.values():
            v.sort()
        for v in self.by_end.values():
            v.sort()
        self.mask = np.zeros((n, Lmax), dtype=bool)
        for s, L in self.runs:
            if L <= Lmax:
                self.mask[s, L - 1] = True

    def prefixes(self, s, L):
        Ls = self.by_start.get(s, [])
        return Ls[:bisect.bisect_left(Ls, L)]

    def suffixes(self, s, L):
        Ls = self.by_end.get(s + L, [])
        return Ls[:bisect.bisect_left(Ls, L)]

    def nested(self, s, L):
        """Primes strictly inside (s, L), as (start, length)."""
        e = s + L
        out = []
        for x in range(s + 1, e - 1):
            Ls = self.by_start.get(x)
            if Ls:
                for L2 in Ls[:bisect.bisect_right(Ls, e - x - 1)]:
                    out.append((x, L2))
        return out

    def inside_any(self, s, L):
        return self.nested(s, L) + [(s, x) for x in self.prefixes(s, L)] + \
            [(s + L - x, x) for x in self.suffixes(s, L)]


def longest_chain(P, d):
    """One longest tower: primes each inside the one before."""
    s, L = np.unravel_index(np.argmax(d), d.shape)
    s, L = int(s), int(L) + 1
    chain = [(s, L)]
    while d[s, L - 1] > 1:
        want = d[s, L - 1] - 1
        for s2, L2 in sorted(P.inside_any(s, L), key=lambda r: -r[1]):
            if d[s2, L2 - 1] == want:
                s, L = s2, L2
                break
        chain.append((s, L))
    return chain


def bridges(P, giant_min=GIANT_MIN):
    """Giants whose longest prime prefix and suffix don't meet, and the
    primes inside each that span the gap."""
    out = dict(giants=0, no_prefix=0, no_suffix=0, meet=0, gap=0,
               bridged=0, bridges=0, examples=[])
    for s, L in P.runs:
        if L < giant_min:
            continue
        out["giants"] += 1
        pre, suf = P.prefixes(s, L), P.suffixes(s, L)
        if not pre:
            out["no_prefix"] += 1
        if not suf:
            out["no_suffix"] += 1
        if not pre or not suf:
            continue
        a, b = s + pre[-1], s + L - suf[-1]      # gap is [a, b)
        if a >= b:
            out["meet"] += 1
            continue
        out["gap"] += 1
        found = [(x, L2) for x in range(s, a + 1)
                 for L2 in P.by_start.get(x, [])
                 if x + L2 >= b and x + L2 <= s + L and (x, L2) != (s, L)]
        out["bridges"] += len(found)
        if found:
            out["bridged"] += 1
            if len(out["examples"]) < 5:
                out["examples"].append(dict(
                    giant=(s, L), prefix=pre[-1], suffix=suf[-1],
                    gap=(a, b), bridge=max(found, key=lambda r: r[1])))
    return out


def covers(P, giant_min=GIANT_MIN):
    """Overlapping pairs of giants, and primes that contain both."""
    giants = sorted((s, s + L) for s, L in P.runs if L >= giant_min)
    starts = np.array([g[0] for g in giants])
    ends = np.array([g[1] for g in giants])
    # For each place x: the furthest end of any prime starting at or before x.
    reach = np.zeros(P.n + 1, dtype=np.int64)
    for s, L in P.runs:
        reach[s] = max(reach[s], s + L)
    reach = np.maximum.accumulate(reach)
    pairs = covered = 0
    for i, (s1, e1) in enumerate(giants):
        j0, j1 = np.searchsorted(starts, [s1 + 1, e1])
        later = ends[j0:j1]
        part = later > e1                # starts inside, ends beyond
        k = int(part.sum())
        pairs += k
        if k:
            covered += int((reach[s1] >= later[part]).sum())
    # Primes containing at least one overlapping pair of giants.
    cover_primes = 0
    for s, L in P.runs:
        if L <= giant_min:               # too short to hold two giants
            continue
        e = s + L
        j0, j1 = np.searchsorted(starts, [s, e])
        far = far_before = -1            # furthest end among earlier starts
        last_start = None
        for a, b in zip(starts[j0:j1], ends[j0:j1]):
            if b > e or (a, b) == (s, e):
                continue
            if a != last_start:
                far_before, last_start = far, a
            if a < far_before < b:       # an earlier giant ends inside this one
                cover_primes += 1
                break
            far = max(far, b)
    return dict(giants=len(giants), overlapping_pairs=pairs,
                pairs_with_cover=covered, cover_primes=cover_primes)


# ---------------------------------------------------------- known cases

# Brian's known cases in Parent One: 0-indexed decimals, end exclusive.
KNOWN = {
    "G1700": (493, 2193), "G1730": (1465, 3195),
    "M2050": (2676, 4726), "S1400": (3326, 4726),
    "G1700 prefix": (493, 952), "G1700 suffix": (639, 2193),
}
KNOWN_FACTS = [
    ("G1700 and G1730 overlap by 728", ("G1700", "G1730"), 728),
]


def known_cases(digits, P):
    """Check each known case directly, and say what the saved primes
    (up to LMAX digits) show inside it."""
    import gmpy2
    out = {}
    for name, (a, b) in KNOWN.items():
        run = digits[a:b]
        inside = [r for r in P.runs if r[0] >= a and r[0] + r[1] <= b
                  and (r[0], r[0] + r[1]) != (a, b)]
        pre = [L for s, L in inside if s == a]
        suf = [L for s, L in inside if s + L == b]
        out[name] = dict(
            start=a, end=b, length=b - a,
            prime=bool(gmpy2.is_prime(gmpy2.mpz(run), 30)),
            in_saved_primes=(a, b - a) in set(P.runs),
            saved_primes_inside=len(inside),
            longest_saved_prefix=max(pre, default=0),
            longest_saved_suffix=max(suf, default=0))
    for text, (x, y), want in KNOWN_FACTS:
        (a1, b1), (a2, b2) = KNOWN[x], KNOWN[y]
        got = min(b1, b2) - max(a1, a2)
        out[text] = dict(computed=got, matches=got == want)
    return out


# ------------------------------------------------------- low entropy

def low_entropy_digits(digits, W):
    """Digits inside the lowest-entropy windows (at most LOW_SHARE of them)."""
    prof = np.array(entropy.entropy_profile(digits, W))
    vals = np.sort(np.unique(np.round(prof, 9)))
    share = lambda v: float((np.round(prof, 9) <= v).mean())
    cut = vals[0]
    for v in vals:
        if share(v) <= LOW_SHARE:
            cut = v
        else:
            break
    low_windows = np.round(prof, 9) <= cut
    diff = np.zeros(len(digits) + 1)
    idx = np.nonzero(low_windows)[0]
    np.add.at(diff, idx, 1)
    np.add.at(diff, idx + W, -1)
    covered = np.cumsum(diff)[:len(digits)] > 0
    return covered, float(cut), float(low_windows.mean())


# --------------------------------------------------------- per stream

def analyse(task):
    name, digits, runs, out_dir = task
    n = len(digits)
    P = Primes(runs, n)
    obs_w = P.mask.astype(float)
    exp_w = chance.run_chance(digits, LMAX)

    res = dict(primes=len(P.runs))
    res["primes_by_band"] = dict(
        observed={f"{a}-{b}": float(obs_w[:, a - 1:b].sum()) for a, b in STACK_BANDS[1:]},
        expected={f"{a}-{b}": float(exp_w[:, a - 1:b].sum()) for a, b in STACK_BANDS[1:]})

    per_o, _, tot_o = tower_counts(obs_w)
    per_e, _, tot_e = tower_counts(exp_w)
    res["towers"] = dict(observed=tot_o, expected=tot_e)
    res["towers_by_outer_band"] = {
        kind: dict(observed=by_band(obs_w, per_o[kind], ((1, 100), (101, 1000))),
                   expected=by_band(exp_w, per_e[kind], ((1, 100), (101, 1000))))
        for kind in per_o}

    d = depth(P.mask)
    chain = longest_chain(P, d)
    hist = np.bincount(d[P.mask])
    res["depth"] = dict(deepest=int(d.max()),
                        chain=[(s + 1, L) for s, L in chain],
                        primes_by_depth={int(k): int(v) for k, v in enumerate(hist) if k})

    ov_o, ov_e = overlap_counts(obs_w), overlap_counts(exp_w)
    k = np.arange(LMAX)
    res["overlaps"] = dict(
        observed=dict(pairs=float(ov_o.sum()), mean_shared=float((k * ov_o).sum() / ov_o.sum()),
                      shared_1_10=float(ov_o[1:11].sum()), shared_11_100=float(ov_o[11:101].sum()),
                      shared_101_999=float(ov_o[101:].sum())),
        expected=dict(pairs=float(ov_e.sum()), mean_shared=float((k * ov_e).sum() / ov_e.sum()),
                      shared_1_10=float(ov_e[1:11].sum()), shared_11_100=float(ov_e[11:101].sum()),
                      shared_101_999=float(ov_e[101:].sum())))

    st_o, st_e = stack_by_band(obs_w), stack_by_band(exp_w)
    res["stack"] = {band: dict(
        observed_mean=float(st_o[band].mean()), expected_mean=float(st_e[band].mean()),
        observed_max=float(st_o[band].max()), max_at_place=int(st_o[band].argmax()) + 1)
        for band in st_o}

    res["bridges"] = bridges(P)
    res["covers"] = covers(P)

    res["low_entropy"] = {}
    starts_o, starts_e = obs_w.sum(axis=1), exp_w.sum(axis=1)
    for W in settings.ENTROPY_WINDOWS:
        low, cut, share = low_entropy_digits(digits, W)
        row = dict(cutoff_bits=cut, share_of_windows=share,
                   share_of_digits=float(low.mean()))
        for band in st_o:
            o, e = st_o[band], st_e[band]
            row[f"stack_{band}"] = dict(
                low_observed=float(o[low].mean()), low_expected=float(e[low].mean()),
                rest_observed=float(o[~low].mean()), rest_expected=float(e[~low].mean()))
        row["starts"] = dict(
            low_observed=float(starts_o[low].mean()), low_expected=float(starts_e[low].mean()),
            rest_observed=float(starts_o[~low].mean()), rest_expected=float(starts_e[~low].mean()))
        res["low_entropy"][W] = row

    if name == "parent_one":
        res["known_cases"] = known_cases(digits, P)
    _write_lists(out_dir, name, P, per_o, d)
    return name, res


def _write_lists(out_dir, name, P, per_o, d):
    """Every prime with its prefixes, suffixes and nested primes."""
    with open(out_dir / f"towers_{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["start_place", "length", "depth", "prefix_lengths",
                    "suffix_lengths", "nested_count"])
        for s, L in P.runs:
            w.writerow([s + 1, L, int(d[s, L - 1]),
                        " ".join(map(str, P.prefixes(s, L))),
                        " ".join(map(str, P.suffixes(s, L))),
                        int(round(per_o["nested"][s, L - 1]))])
    with gzip.open(out_dir / f"nested_{name}.csv.gz", "wt", newline="") as f:
        w = csv.writer(f)
        w.writerow(["outer_start_place", "outer_length",
                    "inner_start_place", "inner_length"])
        for s, L in P.runs:
            for x, L2 in P.nested(s, L):
                w.writerow([s + 1, L, x + 1, L2])


def load_runs(names):
    runs = {n: [] for n in names}
    for pass_name in ("A", "B"):
        path = primes.out_dir() / f"primes_pass_{pass_name}.csv"
        with open(path) as f:
            for row in csv.DictReader(f):
                if row["stream"] in runs:
                    runs[row["stream"]].append(
                        (int(row["start_place"]) - 1, int(row["length"])))
    return runs


def run(cores=3):
    out_dir = RESULTS_DIR / f"D{settings.DECIMAL_PLACES}"
    out_dir.mkdir(parents=True, exist_ok=True)
    stream_set = {n: d for n, (d, _) in streams.load_streams().items()}
    runs = load_runs(stream_set)
    tasks = [(n, d, runs[n], out_dir) for n, d in stream_set.items()]
    with Pool(cores) as pool:
        results = dict(pool.imap_unordered(analyse, tasks))
    summary = dict(
        settings=dict(decimal_places=settings.DECIMAL_PLACES, longest=LMAX,
                      giant_min=GIANT_MIN, low_entropy_share=LOW_SHARE,
                      entropy_windows=list(settings.ENTROPY_WINDOWS)),
        streams={n: results[n] for n in sorted(results)})
    (out_dir / "structure_summary.json").write_text(
        json.dumps(summary, indent=1) + "\n")
    return out_dir, summary


if __name__ == "__main__":
    run()
