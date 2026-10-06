"""Stage 3: the prime search, checked against slow independent methods."""
import random
import tempfile
import unittest
from pathlib import Path

from pi_parents import primes


def slow_is_prime(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def slow_search(digits, lo, hi):
    """Every run of lo..hi digits, by brute force, with Brian's skip rule."""
    found = []
    for s in range(len(digits)):
        for L in range(lo, hi + 1):
            run = digits[s:s + L]
            if len(run) < L or run[0] == "0" or run[-1] in "024568":
                continue
            if slow_is_prime(int(run)):
                found.append((s, L))
    return sorted(found)


class Search(unittest.TestCase):
    P = primes.primorial()

    def test_small_primes_below_trial_bound_are_kept(self):
        for p in (11, 13, 97, 1009, 19997):
            self.assertTrue(primes.is_prime(primes.mpz(p), self.P))
        for c in (21, 91, 1001, 19999):
            self.assertFalse(primes.is_prime(primes.mpz(c), self.P))

    def test_matches_brute_force(self):
        rng = random.Random(7)
        digits = "".join(rng.choice("0123456789") for _ in range(400))
        got, _, _ = primes.search(digits, range(len(digits)), 2, 9, self.P)
        self.assertEqual(sorted(got), slow_search(digits, 2, 9))

    def test_pass_split_loses_nothing(self):
        # Two passes over 2..6 and 7..12 find what one pass over 2..12 does.
        rng = random.Random(8)
        digits = "".join(rng.choice("0123456789") for _ in range(300))
        whole, _, _ = primes.search(digits, range(300), 2, 12, self.P)
        a, _, _ = primes.search(digits, range(300), 2, 6, self.P)
        b, _, _ = primes.search(digits, range(300), 7, 12, self.P)
        self.assertEqual(sorted(whole), sorted(a + b))

    def test_skip_rule_and_counts(self):
        # "1037": runs from start 0 of lengths 2..4 are 10, 103, 1037.
        # 10 ends in 0 (skipped); 103 is prime; 1037 = 17 * 61.
        found, tested, _ = primes.search("1037", [0], 2, 4, self.P)
        self.assertEqual(found, [(0, 3)])
        self.assertEqual(tested, {3: 1, 4: 1})
        # A start on 0 is skipped entirely.
        self.assertEqual(primes.search("0373", [0], 2, 4, self.P)[1], {})

    def test_run_never_passes_end_of_stream(self):
        found, tested, _ = primes.search("1131", range(4), 2, 10, self.P)
        self.assertEqual(sorted(found), [(0, 2), (0, 3), (1, 2), (1, 3), (2, 2)])
        self.assertEqual(max(tested), 4)

    def test_short_chance_table(self):
        for L in (2, 3, 4, 5):
            runs = [n for n in range(10 ** (L - 1), 10 ** L) if n % 10 in (1, 3, 7, 9)]
            share = sum(map(slow_is_prime, runs)) / len(runs)
            self.assertAlmostEqual(primes.chance_short(L), share, places=12)

    def test_large_known_prime(self):
        # 10^100 + 267 is the first prime above a googol.
        digits = str(10 ** 100 + 267)
        found, _, _ = primes.search(digits, [0], 101, 101, self.P)
        self.assertEqual(found, [(0, 101)])


class Resume(unittest.TestCase):
    def test_stopped_run_resumes_to_the_same_answer(self):
        rng = random.Random(9)
        stream_set = {
            name: ("".join(rng.choice("0123456789") for _ in range(240)), 1)
            for name in ("x", "y")}
        saved = primes.RESULTS_DIR
        with tempfile.TemporaryDirectory() as tmp:
            primes.RESULTS_DIR = Path(tmp)
            try:
                base = primes.run(("A", "B"), stream_set, "t", cores=2)
                full = (base / "primes_pass_B.csv").read_text()
                summary = (base / "summary_pass_A.json").read_text()
                # Lose some pieces and the merged files, as if stopped.
                for pieces in base.glob("pieces_pass_*/x"):
                    for f in sorted(pieces.glob("*.json"))[:1]:
                        f.unlink()
                for f in base.glob("*_pass_*.*"):
                    f.unlink()
                primes.run(("A", "B"), stream_set, "t", cores=2)
                self.assertEqual((base / "primes_pass_B.csv").read_text(), full)
                self.assertEqual((base / "summary_pass_A.json").read_text(),
                                 summary)
            finally:
                primes.RESULTS_DIR = saved
        # Pass B holds only runs longer than 100 digits.
        rows = [tuple(r.split(",")) for r in full.splitlines()[1:]]
        self.assertTrue(rows)
        self.assertTrue(all(101 <= int(L) <= 240 for _, _, L in rows))


if __name__ == "__main__":
    unittest.main()
