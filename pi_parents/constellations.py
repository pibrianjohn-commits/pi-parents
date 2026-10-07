"""Stage 4 (first part): prime constellations, two separate tests.

(a) Membership as numbers. For every prime run found in Stage 3, which
    constellations its value belongs to, whether or not the other members
    appear anywhere in the stream.
(b) Members side by side in the stream. Places where every member of one
    constellation appears as a prime run, all inside a stretch of W
    digits. A "set" is one run for each member; its span runs from the
    first member's first digit to the last digit of whichever member ends
    last.

The constellations are the standard tightest patterns (offsets from the
smallest member):
    twin (0, 2)   cousin (0, 4)   sexy (0, 6)
    triplet (0, 2, 6) or (0, 4, 6)
    quadruplet (0, 2, 6, 8)
    quintuplet (0, 2, 6, 8, 12) or (0, 4, 6, 10, 12)
    sextuplet (0, 4, 6, 10, 12, 16)
    Sophie Germain pair (p, 2p + 1)
"""
import csv
import json
import math
from bisect import bisect_left, bisect_right
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path

from gmpy2 import mpz

from . import chance, primes, settings, streams

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "stage4"

PATTERNS = {
    "twin": [(0, 2)],
    "cousin": [(0, 4)],
    "sexy": [(0, 6)],
    "triplet": [(0, 2, 6), (0, 4, 6)],
    "quadruplet": [(0, 2, 6, 8)],
    "quintuplet": [(0, 2, 6, 8, 12), (0, 4, 6, 10, 12)],
    "sextuplet": [(0, 4, 6, 10, 12, 16)],
}
# Membership columns for test (a). A Sophie Germain prime p has 2p + 1
# prime; its partner 2p + 1 is called a safe prime.
MEMBERSHIP = list(PATTERNS)[:3] + ["sophie_germain", "safe"] + list(PATTERNS)[3:]
# Test (b) looks for every pattern, plus the Sophie Germain pair.
SETS = list(PATTERNS) + ["sophie_germain"]
STRETCHES = (20, 50, 100)

_P = None


def _prime(v):
    return v > 1 and primes.is_prime(mpz(v), _P)


def membership(p):
    """Which constellations the number p belongs to, as a dict of bools."""
    known = {0: True}

    def near(d):                     # is p + d prime? each tested once
        if d not in known:
            known[d] = (p % 2 == 0 or d % 2 == 0) and _prime(p + d)
        return known[d]

    out = {}
    for name, pats in PATTERNS.items():
        out[name] = any(all(near(r - q) for r in pat)
                        for pat in pats for q in pat)
    out["sophie_germain"] = _prime(2 * p + 1)
    out["safe"] = p > 2 and p % 2 == 1 and _prime((p - 1) // 2)
    return out


def member_values(name, base):
    """Each way of writing a constellation with smallest member base."""
    if name == "sophie_germain":
        return [(base, 2 * base + 1)]
    return [tuple(base + o for o in pat) for pat in PATTERNS[name]]


def count_sets(occurrences, W, keep=None):
    """Number of ways to pick one run per member, all within W digits.

    occurrences: for each member, a sorted list of (start, length).
    keep: if a list, each set found is added to it as (span, runs).
    """
    starts = [[s for s, _ in occ] for occ in occurrences]
    total = 0
    chosen = []

    def extend(i, lo, hi):
        # lo = earliest start so far, hi = latest end so far
        nonlocal total
        if i == len(occurrences):
            total += 1
            if keep is not None:
                keep.append((hi - lo, tuple(chosen)))
            return
        occ = occurrences[i]
        a = bisect_left(starts[i], hi - W)
        b = bisect_right(starts[i], lo + W)
        for s, L in occ[a:b]:
            nlo, nhi = min(lo, s), max(hi, s + L)
            if nhi - nlo <= W:
                chosen.append((s, L))
                extend(i + 1, nlo, nhi)
                chosen.pop()

    for s, L in occurrences[0]:
        if L <= W:
            chosen.append((s, L))
            extend(1, s, s + L)
            chosen.pop()
    return total


def side_by_side(runs, digits, stretches=STRETCHES, keep=False):
    """Test (b) for one stream.

    runs: prime runs as (start index, length). Returns, for every
    constellation and stretch, the number of sets and the number of
    distinct constellations (sets of values) seen at least once; and, if
    keep, every set within the widest stretch.
    """
    where = defaultdict(list)
    for s, L in runs:
        if L <= max(stretches):
            where[int(digits[s:s + L])].append((s, L))
    for occ in where.values():
        occ.sort()
    out = {name: {W: dict(sets=0, distinct=0) for W in stretches}
           for name in SETS}
    found = []
    for base in sorted(where):
        for name in SETS:
            for members in member_values(name, base):
                if not all(m in where for m in members):
                    continue
                occ = [where[m] for m in members]
                for W in stretches:
                    n = count_sets(occ, W)
                    out[name][W]["sets"] += n
                    out[name][W]["distinct"] += n > 0
                if keep:
                    sets = []
                    count_sets(occ, max(stretches), sets)
                    found.extend((name, members, span, chosen)
                                 for span, chosen in sets)
    return out, found


def analyse_stream(task):
    """Both tests for one stream, with the membership chance figures."""
    global _P
    if _P is None:
        _P = primes.primorial()
    name, digits, runs_by_pass = task
    memo, flags, counts, expected = {}, {}, {}, {}
    for pass_name, runs in runs_by_pass.items():
        c = dict.fromkeys(MEMBERSHIP, 0)
        x = dict.fromkeys(MEMBERSHIP, 0.0)
        c["primes"] = len(runs)
        rows = []
        for s, L in runs:
            v = int(digits[s:s + L])
            if v not in memo:
                memo[v] = (membership(v),
                           {k: chance.member_chance(k, v) for k in MEMBERSHIP})
            m, ch = memo[v]
            for k in MEMBERSHIP:
                c[k] += m[k]
                x[k] += ch[k]
            rows.append((s, L, m))
        counts[pass_name], expected[pass_name] = c, x
        flags[pass_name] = rows
    sides, found = side_by_side(runs_by_pass["A"], digits, keep=True)
    return name, counts, expected, sides, flags, found


def instances(pair_limit=10 ** 6, group_limit=10 ** 4):
    """Every constellation whose members are small enough to matter for
    the chance figure in test (b): pairs with members below pair_limit,
    larger groups below group_limit. Bigger ones add less than 0.001."""
    top = 2 * pair_limit + 40
    sieve = bytearray([1]) * (top + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(top ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(range(p * p, top + 1, p)))
    out = {name: [] for name in SETS}
    for base in range(2, pair_limit):
        if not sieve[base]:
            continue
        for name in SETS:
            limit = pair_limit if name in ("twin", "cousin", "sexy",
                                           "sophie_germain") else group_limit
            if base >= limit:
                continue
            for members in member_values(name, base):
                if all(sieve[m] for m in members):
                    out[name].append(members)
    return out


def expected_side_by_side(n, stretches=STRETCHES):
    """Chance figures for test (b): sets, and constellations seen at least
    once (taking each constellation's count as Poisson)."""
    out = {name: {W: dict(sets=0.0, distinct=0.0) for W in stretches}
           for name in SETS}
    for name, group in instances().items():
        for members in group:
            for W in stretches:
                if len(str(members[-1])) > W:
                    continue
                if len(members) == 2:
                    e = chance.expected_pair_sets(*members, n, W)
                else:
                    e = chance.expected_sets(members, n, W)
                out[name][W]["sets"] += e
                out[name][W]["distinct"] += 1 - math.exp(-e)
    return out


def load_runs(wanted):
    """Prime runs from Stage 3, as start index and length, by pass."""
    runs = {n: {"A": [], "B": []} for n in wanted}
    for pass_name in ("A", "B"):
        path = primes.out_dir() / f"primes_pass_{pass_name}.csv"
        with open(path) as f:
            for row in csv.DictReader(f):
                if row["stream"] in runs:
                    runs[row["stream"]][pass_name].append(
                        (int(row["start_place"]) - 1, int(row["length"])))
    return runs


def run(cores=3):
    out_dir = RESULTS_DIR / f"D{settings.DECIMAL_PLACES}"
    out_dir.mkdir(parents=True, exist_ok=True)
    main = {n: d for n, (d, _) in streams.load_streams().items()}
    runs = load_runs(main)
    chance.exact_member_shares()     # once, before the workers start
    results = {}
    with Pool(cores) as pool:
        for name, counts, expected, sides, flags, found in pool.imap_unordered(
                analyse_stream, [(n, d, runs[n]) for n, d in main.items()]):
            results[name] = dict(membership=counts,
                                 membership_expected=expected,
                                 side_by_side=sides)
            _write_main(out_dir, name, flags, found)
    summary = dict(
        settings=dict(decimal_places=settings.DECIMAL_PLACES,
                      stretches=list(STRETCHES), patterns=PATTERNS),
        side_by_side_expected=expected_side_by_side(settings.DECIMAL_PLACES),
        streams={n: results[n] for n in sorted(results)})
    (out_dir / "constellations_summary.json").write_text(
        json.dumps(summary, indent=1) + "\n")
    return out_dir, summary


def _write_main(out_dir, name, flags, found):
    for pass_name, rows in flags.items():
        with open(out_dir / f"membership_{name}_pass_{pass_name}.csv", "w",
                  newline="") as f:
            w = csv.writer(f)
            w.writerow(["start_place", "length"] + MEMBERSHIP)
            for s, L, m in rows:
                w.writerow([s + 1, L] + [int(m[k]) for k in MEMBERSHIP])
    # Every set within the widest stretch; narrower ones have smaller spans.
    with open(out_dir / f"close_sets_{name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["constellation", "members", "span", "runs (place:length)"])
        for cname, members, span, chosen in found:
            w.writerow([cname, " ".join(map(str, members)), span,
                        " ".join(f"{s + 1}:{L}" for s, L in chosen)])


if __name__ == "__main__":
    run()
