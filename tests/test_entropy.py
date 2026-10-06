"""Stage 2: the sliding entropy profile."""
import math
import random
import unittest

from pi_parents import entropy, streams


class Profile(unittest.TestCase):
    def test_single_repeated_digit_is_zero(self):
        self.assertEqual(entropy.entropy_profile("7" * 60, 50), [0.0] * 11)

    def test_all_ten_digits_evenly_is_log2_10(self):
        prof = entropy.entropy_profile("0123456789" * 8, 50)
        for h in prof:
            self.assertAlmostEqual(h, math.log2(10), places=12)

    def test_two_digits_evenly_is_one_bit(self):
        self.assertAlmostEqual(entropy.entropy_profile("01" * 25, 50)[0], 1.0)

    def test_sliding_matches_direct_count(self):
        rng = random.Random(1)
        digits = "".join(rng.choice("0123456789") for _ in range(5_000))
        for W in (1, 7, 50, 200):
            prof = entropy.entropy_profile(digits, W)
            self.assertEqual(len(prof), len(digits) - W + 1)
            for i in range(0, len(prof), 37):
                self.assertAlmostEqual(
                    prof[i], entropy.window_entropy(digits[i:i + W]), places=9)

    def test_parents_match_direct_count_everywhere(self):
        for name, (digits, _) in streams.load_streams(10_000, False).items():
            prof = entropy.entropy_profile(digits, 50)
            for i, h in enumerate(prof):
                self.assertAlmostEqual(
                    h, entropy.window_entropy(digits[i:i + 50]), places=9,
                    msg=f"{name} window {i}")

    def test_most_possible(self):
        self.assertAlmostEqual(entropy.max_entropy(10), math.log2(10))
        self.assertAlmostEqual(entropy.max_entropy(20), math.log2(10))
        # 12 digits: two digits appear twice, eight appear once.
        self.assertAlmostEqual(entropy.max_entropy(12),
                               entropy.window_entropy("001123456789"))
        for W in (10, 12, 15, 20, 30, 50):
            rng = random.Random(W)
            digits = "".join(rng.choice("0123456789") for _ in range(2_000))
            self.assertLessEqual(max(entropy.entropy_profile(digits, W)),
                                 entropy.max_entropy(W) + 1e-12)

    def test_every_chosen_size_matches_direct_count(self):
        digits = streams.load_streams(10_000, False)["parent_two"][0]
        for W in (10, 12, 15, 20, 30, 50):
            prof = entropy.entropy_profile(digits, W)
            self.assertEqual(len(prof), 10_001 - W)
            for i in range(0, len(prof), 13):
                self.assertAlmostEqual(
                    prof[i], entropy.window_entropy(digits[i:i + W]), places=9)

    def test_window_too_long(self):
        with self.assertRaises(ValueError):
            entropy.entropy_profile("123", 4)


class Streams(unittest.TestCase):
    def test_decimals_only(self):
        s = streams.load_streams(10_000, False)
        self.assertEqual(s["parent_one"][0][:6], "383045")
        self.assertEqual(s["parent_two"][0][:6], "758546")
        self.assertEqual(s["pi"][0][:6], "141592")
        for digits, first_place in s.values():
            self.assertEqual((len(digits), first_place), (10_000, 1))

    def test_leading_digit_included(self):
        s = streams.load_streams(10_000, True)
        self.assertEqual(s["parent_one"], (s["parent_one"][0], 0))
        self.assertEqual(s["parent_one"][0][:6], "238304")
        self.assertEqual(s["pi"][0][:6], "314159")
        # Parent Two's leading 0 is never part of the stream.
        self.assertEqual(s["parent_two"][0][:6], "758546")
        self.assertEqual(s["parent_two"][1], 1)


if __name__ == "__main__":
    unittest.main()
