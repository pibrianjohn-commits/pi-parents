"""Stage 4 constellations, checked against brute force."""
import itertools
import math
import random
import unittest

from pi_parents import constellations as C, primes
from tests.test_primes import slow_is_prime, slow_search


def setUpModule():
    C._P = primes.primorial()


def slow_membership(p):
    pr = slow_is_prime
    out = {}
    for name, pats in C.PATTERNS.items():
        out[name] = any(all(pr(p - q + r) for r in pat)
                        for pat in pats for q in pat)
    out["sophie_germain"] = pr(2 * p + 1)
    out["safe"] = p % 2 == 1 and pr((p - 1) // 2)
    return out


class Membership(unittest.TestCase):
    def test_small_cases(self):
        m = C.membership(5)
        for k in ("twin", "sexy", "sophie_germain", "safe", "triplet",
                  "quadruplet", "quintuplet"):
            self.assertTrue(m[k], k)
        self.assertFalse(m["cousin"])
        self.assertFalse(m["sextuplet"])
        self.assertTrue(C.membership(7)["sextuplet"])      # 7 11 13 17 19 23
        self.assertTrue(C.membership(23)["sextuplet"])
        self.assertFalse(C.membership(97)["twin"])         # 95, 99
        self.assertTrue(C.membership(97)["cousin"])         # 97, 101
        self.assertFalse(C.membership(2)["twin"])
        self.assertTrue(C.membership(2)["sophie_germain"])  # 2, 5

    def test_matches_brute_force(self):
        for p in range(2, 5_000):
            if slow_is_prime(p):
                self.assertEqual(C.membership(p), slow_membership(p), p)

    def test_large_primes(self):
        import gmpy2
        # 30-digit primes, including the first twin pair above 10^29.
        p, checked, twins = gmpy2.next_prime(10 ** 29), 0, 0
        while twins == 0 or checked < 200:
            m = C.membership(int(p))
            self.assertEqual(m, slow_membership_big(int(p)))
            twins += m["twin"]
            checked += 1
            p = gmpy2.next_prime(p)


def slow_membership_big(p):
    import gmpy2
    pr = lambda n: n > 1 and gmpy2.is_prime(n, 60)
    out = {}
    for name, pats in C.PATTERNS.items():
        out[name] = any(all(pr(p - q + r) for r in pat)
                        for pat in pats for q in pat)
    out["sophie_germain"] = pr(2 * p + 1)
    out["safe"] = p % 2 == 1 and pr((p - 1) // 2)
    return out


class Sets(unittest.TestCase):
    def test_count_sets_matches_brute_force(self):
        rng = random.Random(3)
        for _ in range(200):
            occ = [sorted((rng.randrange(60), rng.randint(1, 4))
                          for _ in range(rng.randint(0, 6)))
                   for _ in range(rng.randint(2, 4))]
            W = rng.choice((5, 10, 20))
            brute = sum(
                1 for pick in itertools.product(*occ)
                if max(s + L for s, L in pick) - min(s for s, _ in pick) <= W)
            self.assertEqual(C.count_sets(occ, W), brute)

    def test_side_by_side_matches_brute_force(self):
        rng = random.Random(4)
        digits = "".join(rng.choice("0123456789") for _ in range(600))
        runs = slow_search(digits, 1, 12)
        got, found = C.side_by_side(runs, digits, (20, 50), keep=True)
        # Brute force: every pick of runs whose values form a constellation.
        value = {r: int(digits[r[0]:r[0] + r[1]]) for r in runs}
        for name in C.SETS:
            for W in (20, 50):
                n = 0
                bases = {value[r] for r in runs}
                for base in bases:
                    for members in C.member_values(name, base):
                        occ = [[r for r in runs if value[r] == m] for m in members]
                        n += sum(
                            1 for pick in itertools.product(*occ)
                            if max(s + L for s, L in pick)
                            - min(s for s, _ in pick) <= W)
                self.assertEqual(got[name][W]["sets"], n, (name, W))
        self.assertEqual(len(found), sum(got[n][50]["sets"] for n in C.SETS))

    def test_simple_twin(self):
        out, _ = C.side_by_side([(0, 1), (1, 1)], "35", (20,))
        self.assertEqual(out["twin"][20], dict(sets=1, distinct=1))
        # 3 and 5 also form a Sophie Germain pair? No: 2*3+1 = 7.
        self.assertEqual(out["sophie_germain"][20]["sets"], 0)

    def test_stretch_limit(self):
        digits = "3" + "0" * 18 + "5"           # 3 ... 5 spans 20 digits
        runs = [(0, 1), (19, 1)]
        self.assertEqual(C.side_by_side(runs, digits, (19, 20))[0]["twin"],
                         {19: dict(sets=0, distinct=0), 20: dict(sets=1, distinct=1)})


if __name__ == "__main__":
    unittest.main()


class Chance(unittest.TestCase):
    def test_hardy_littlewood_constants(self):
        from pi_parents import chance
        known = {(0, 2): 1.3203236, (0, 2, 6): 2.8582486, (0, 4, 6): 2.8582486,
                 (0, 2, 6, 8): 4.1511809, (0, 2, 6, 8, 12): 10.1317949,
                 (0, 4, 6, 10, 12, 16): 17.2986123}
        for H, c in known.items():
            self.assertAlmostEqual(chance.singular_series(H), c, places=4)
        self.assertEqual(chance.singular_series((0, 2, 4)), 0.0)

    def test_formula_close_to_exact_at_seven_digits(self):
        from pi_parents import chance
        exact = chance.exact_member_shares()[7]
        ln_p = math.log(5 * 10 ** 6)
        for name in ("twin", "cousin", "sexy", "sophie_germain", "triplet"):
            f = chance.member_chance_formula(name, ln_p)
            self.assertLess(abs(f / exact[name] - 1), 0.12, name)

    def test_expected_sets_exhaustive(self):
        from pi_parents import chance
        n = 5
        for members, W in (((3, 5), 3), ((11, 13), 4), ((5, 7, 11), 4),
                           ((2, 5), 5), ((13, 31), 4)):
            words = [str(m) for m in members]
            total = 0
            for x in range(10 ** n):
                s = str(x).zfill(n)
                occ = [[(i, len(w)) for i in range(n) if s.startswith(w, i)]
                       for w in words]
                total += C.count_sets(occ, W)
            self.assertAlmostEqual(chance.expected_sets(members, n, W),
                                   total / 10 ** n, places=12, msg=members)
            if len(members) == 2:
                self.assertAlmostEqual(chance.expected_pair_sets(*members, n, W),
                                       total / 10 ** n, places=12)
