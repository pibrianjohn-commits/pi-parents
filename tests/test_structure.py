"""Stage 4 structure counts, checked against slow direct versions."""
import itertools
import math
import random
import unittest

import numpy as np

from pi_parents import chance, structure as S
from tests.test_primes import slow_search

N, LMAX = 160, 14


def random_runs(seed):
    rng = random.Random(seed)
    digits = "".join(rng.choice("0123456789") for _ in range(N))
    return digits, slow_search(digits, 1, LMAX)


def inside(a, b):
    """Run b lies within run a (and is not a)."""
    return a != b and b[0] >= a[0] and b[0] + b[1] <= a[0] + a[1]


def kind(a, b):
    if b[0] == a[0]:
        return "prefix"
    if b[0] + b[1] == a[0] + a[1]:
        return "suffix"
    return "nested"


class Towers(unittest.TestCase):
    def test_observed_counts(self):
        digits, runs = random_runs(1)
        P = S.Primes(runs, N, LMAX)
        per, _, tot = S.tower_counts(P.mask.astype(float))
        pairs = {"prefix": 0, "suffix": 0, "nested": 0}
        with_ = {"prefix": set(), "suffix": set(), "nested": set()}
        for a in runs:
            for b in runs:
                if inside(a, b):
                    k = kind(a, b)
                    pairs[k] += 1
                    with_[k].add(a)
        for k in pairs:
            self.assertAlmostEqual(tot[f"{k}_pairs"], pairs[k])
            self.assertAlmostEqual(tot[f"with_{k}"], len(with_[k]))
        self.assertAlmostEqual(tot["with_prefix_and_suffix"],
                               len(with_["prefix"] & with_["suffix"]))
        # Per-prime lists agree with the arrays.
        for s, L in runs:
            self.assertEqual(len(P.prefixes(s, L)), per["prefix"][s, L - 1])
            self.assertEqual(len(P.suffixes(s, L)), per["suffix"][s, L - 1])
            self.assertEqual(len(P.nested(s, L)), per["nested"][s, L - 1])

    def test_expected_counts(self):
        rng = random.Random(2)
        n, Lmax = 40, 7
        w = np.array([[rng.random() * 0.5 if s + L <= n else 0.0
                       for L in range(1, Lmax + 1)] for s in range(n)])
        _, _, tot = S.tower_counts(w)
        runs = [(s, L) for s in range(n) for L in range(1, Lmax + 1) if s + L <= n]
        q = lambda r: w[r[0], r[1] - 1]
        for k in ("prefix", "suffix", "nested"):
            pairs = sum(q(a) * q(b) for a in runs for b in runs
                        if inside(a, b) and kind(a, b) == k)
            atleast = sum(q(a) * (1 - math.prod(1 - q(b) for b in runs
                                                if inside(a, b) and kind(a, b) == k))
                          for a in runs)
            self.assertAlmostEqual(tot[f"{k}_pairs"], pairs)
            self.assertAlmostEqual(tot[f"with_{k}"], atleast)


class Others(unittest.TestCase):
    def test_overlaps(self):
        digits, runs = random_runs(3)
        P = S.Primes(runs, N, LMAX)
        got = S.overlap_counts(P.mask.astype(float))
        want = np.zeros(LMAX)
        for a, b in itertools.permutations(runs, 2):
            if a[0] < b[0] < a[0] + a[1] < b[0] + b[1]:
                want[a[0] + a[1] - b[0]] += 1
        self.assertTrue(np.allclose(got, want))

    def test_stack(self):
        digits, runs = random_runs(4)
        P = S.Primes(runs, N, LMAX)
        got = S.stack(P.mask.astype(float))
        want = [sum(1 for s, L in runs if s <= t < s + L) for t in range(N)]
        self.assertTrue(np.allclose(got, want))

    def test_depth(self):
        digits, runs = random_runs(5)
        P = S.Primes(runs, N, LMAX)
        d = S.depth(P.mask)
        memo = {}

        def deep(a):
            if a not in memo:
                memo[a] = 1 + max([deep(b) for b in runs if inside(a, b)], default=0)
            return memo[a]
        for r in runs:
            self.assertEqual(d[r[0], r[1] - 1], deep(r))
        chain = S.longest_chain(P, d)
        self.assertEqual(len(chain), d.max())
        for a, b in zip(chain, chain[1:]):
            self.assertTrue(inside(a, b))

    def test_bridges_and_covers(self):
        # Giant 0..10 with prefix 0..3 and suffix 7..10; bridge 2..8.
        runs = [(0, 10), (0, 3), (7, 3), (2, 6), (3, 2)]
        P = S.Primes(runs, 20, 12)
        b = S.bridges(P, giant_min=10)
        self.assertEqual((b["giants"], b["gap"], b["bridged"], b["bridges"]),
                         (1, 1, 1, 1))
        # Giants 0..6 and 4..10 overlap; 0..12 covers both.
        runs = [(0, 6), (4, 6), (0, 12)]
        c = S.covers(S.Primes(runs, 20, 12), giant_min=6)
        self.assertEqual(c["overlapping_pairs"], 1)
        self.assertEqual(c["pairs_with_cover"], 1)
        self.assertEqual(c["cover_primes"], 1)
        # Same start is containment, not overlap.
        c = S.covers(S.Primes([(0, 6), (0, 8), (0, 12)], 20, 12), giant_min=6)
        self.assertEqual((c["overlapping_pairs"], c["cover_primes"]), (0, 0))

    def test_run_chance_matches_stage3(self):
        digits, _ = random_runs(6)
        q = chance.run_chance(digits, LMAX)
        from pi_parents import primes
        _, _, expected = primes.search(digits, range(N), 1, LMAX)
        for L in range(1, LMAX + 1):
            self.assertAlmostEqual(q[:, L - 1].sum(), expected.get(L, 0.0))


if __name__ == "__main__":
    unittest.main()
