"""Stage 1: the pi parents generator.

Exact whole-number arithmetic throughout (no floating point):

1. pi to D decimal places, by Machin's formula.
2. Continued-fraction convergents of pi, stepped in order (3/1 is the 1st),
   until the first whose quotient matches pi in all D places.
3. Pi's digit string, as one whole number, split in the ratio
   numerator : denominator at D + 2 places, then truncated to D places.
   The larger part is Parent One, the smaller part Parent Two.
"""
import sys
from pathlib import Path

sys.set_int_max_str_digits(0)

GUARD_DIGITS = 2
DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def arctan_inv(x, one):
    """arctan(1/x) * one, by its power series."""
    total = term = one // x
    x2, n, sign = x * x, 1, 1
    while term:
        term //= x2
        n += 2
        sign = -sign
        total += sign * (term // n)
    return total


def pi_scaled(places, guard=30):
    """floor(pi * 10^places)."""
    one = 10 ** (places + guard)
    p = 4 * (4 * arctan_inv(5, one) - arctan_inv(239, one))
    return p // 10 ** guard


def make_parents(D=10_000, guard=GUARD_DIGITS):
    work = D + 60                      # extra precision for the CF expansion
    P = pi_scaled(work)                # pi ~ P / 10^work
    target = P // 10 ** (work - D)     # pi truncated to D places, as 3141...

    # Continued fraction of P / 10^work, stepping through the convergents.
    a, b = P, 10 ** work
    h0, h1, k0, k1 = 0, 1, 1, 0
    n = 0
    while True:
        q, r = divmod(a, b)
        h0, h1 = h1, q * h1 + h0
        k0, k1 = k1, q * k1 + k0
        n += 1                         # n = 1 for a0 = 3/1
        if (h1 * 10 ** D) // k1 == target:
            break
        a, b = b, r
    num, den = h1, k1

    # Split pi's digit string in ratio num : den at D + guard places.
    G = 10 ** guard
    big = (target * G * num) // (num + den)
    small = (target * G * den) // (num + den)
    one, two = big // G, small // G

    # The same split done exactly, with no guard digits, for comparison.
    exact_one = (target * num) // (num + den)
    exact_two = (target * den) // (num + den)
    return dict(D=D, n=n, num=num, den=den, pi=target, one=one, two=two,
                exact_ok=(one == exact_one and two == exact_two))


def make_parents_from_pi(D, guard=40):
    """Parent One = pi^2 / (pi + 1) and Parent Two = pi / (pi + 1), each
    truncated to D places. Brian's formula for 100,000 places: the same
    split, with pi itself in place of a convergent.

    pi comes from Machin's formula and is checked against MPFR's own pi.
    """
    import gmpy2
    from gmpy2 import mpz
    W = D + guard
    one = mpz(10) ** W
    extra = mpz(10) ** 20            # the series' rounding stays in here
    pi_w = 4 * (4 * arctan_inv(mpz(5), one * extra)
                - arctan_inv(mpz(239), one * extra)) // extra
    gmpy2.get_context().precision = int(W * 3.33) + 64
    check = mpz(gmpy2.floor(gmpy2.const_pi() * one))
    if abs(check - pi_w) > 1:
        raise ArithmeticError("Machin's pi and MPFR's pi disagree")
    # pi_w ~ pi * 10^W to within a unit; that stays in the guard digits.
    p1_w = pi_w * pi_w // (pi_w + one)
    p2_w = pi_w * one // (pi_w + one)
    G = mpz(10) ** guard
    for x in (pi_w, p1_w, p2_w):
        tail = int(x % G)
        if tail < 100 or tail > G - 100:     # a carry could reach place D
            raise ArithmeticError("guard digits too close to a boundary")
    return dict(D=D, pi=int(pi_w // G), one=int(p1_w // G), two=int(p2_w // G))


def fmt(x, D):
    """Whole number x scaled by 10^D, written as a decimal."""
    s = str(x).rjust(D + 1, "0")
    return s[:-D] + "." + s[-D:]


def parent_files(D):
    return {name: DATA_DIR / f"{name}_{D}.txt"
            for name in ("pi", "parent_one", "parent_two")}


def save(r):
    DATA_DIR.mkdir(exist_ok=True)
    files = parent_files(r["D"])
    for name, key in (("pi", "pi"), ("parent_one", "one"), ("parent_two", "two")):
        files[name].write_text(fmt(r[key], r["D"]) + "\n")
    return files


def load(D=10_000):
    """The three numbers as decimal strings, generating and saving if needed."""
    files = parent_files(D)
    if not all(f.exists() for f in files.values()):
        # 10,000 places by the convergent method (the Stage 1 check values);
        # other sizes by Brian's formula, pi^2/(pi+1) and pi/(pi+1).
        save(make_parents(D) if D == 10_000 else make_parents_from_pi(D))
    return {name: f.read_text().strip() for name, f in files.items()}


def report(r):
    D = r["D"]
    one, two = fmt(r["one"], D), fmt(r["two"], D)
    return "\n".join([
        f"decimal places:        {D:,}",
        f"convergent index:      {r['n']:,}",
        f"numerator   digits:    {len(str(r['num'])):,}  {str(r['num'])[:20]}...",
        f"denominator digits:    {len(str(r['den'])):,}  {str(r['den'])[:20]}...",
        f"Parent One:            {one[:32]} ... {one[-10:]}",
        f"Parent Two:            {two[:32]} ... {two[-10:]}",
        f"exact truncation match: {r['exact_ok']}",
        f"pi - (one + two) in last place: {r['pi'] - r['one'] - r['two']}",
    ])


if __name__ == "__main__":
    D = int(sys.argv[1]) if len(sys.argv) > 1 else 10_000
    r = make_parents(D)
    print(report(r))
    for f in save(r).values():
        print("saved", f.relative_to(DATA_DIR.parent))
