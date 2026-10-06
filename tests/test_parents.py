"""Stage 1: the generator must reproduce Brian's check values."""
import unittest

from pi_parents import parents

PI_START = "3.14159265358979323846264338327950288419716939937510"


class CheckValues(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = parents.make_parents(10_000)
        cls.one = parents.fmt(cls.r["one"], 10_000)
        cls.two = parents.fmt(cls.r["two"], 10_000)

    def test_pi(self):
        pi = parents.fmt(self.r["pi"], 10_000)
        self.assertTrue(pi.startswith(PI_START))
        self.assertEqual(len(pi), 10_002)

    def test_convergent_index(self):
        self.assertEqual(self.r["n"], 9_759)

    def test_numerator_and_denominator(self):
        num, den = str(self.r["num"]), str(self.r["den"])
        self.assertEqual(len(num), 5_001)
        self.assertEqual(len(den), 5_001)
        self.assertTrue(num.startswith("32368563035339958784"))
        self.assertTrue(den.startswith("10303233615711916189"))

    def test_parent_one(self):
        self.assertTrue(self.one.startswith("2.383045660595017093118212694234"))
        self.assertTrue(self.one.endswith("6695841427"))
        self.assertEqual(len(self.one), 10_002)

    def test_parent_two(self):
        self.assertTrue(self.two.startswith("0.758546992994776145344430689044"))
        self.assertTrue(self.two.endswith("8560534250"))
        self.assertEqual(len(self.two), 10_002)

    def test_exact_truncation(self):
        self.assertTrue(self.r["exact_ok"])

    def test_parents_sum_to_pi_less_one_in_last_place(self):
        self.assertEqual(self.r["pi"] - self.r["one"] - self.r["two"], 1)

    def test_saved_files_match(self):
        saved = parents.load(10_000)
        self.assertEqual(saved["parent_one"], self.one)
        self.assertEqual(saved["parent_two"], self.two)


class SmallCases(unittest.TestCase):
    def test_first_convergents(self):
        # 3/1, 22/7, 333/106, 355/113: 355/113 is the first good to 6 places.
        r = parents.make_parents(6)
        self.assertEqual((r["n"], r["num"], r["den"]), (4, 355, 113))


if __name__ == "__main__":
    unittest.main()
