"""Chance figures for Stage 4: what prime density alone would give.

Three formulas, each an extension of the one Stage 3 uses for prime counts
(a run not divisible by 2 or 5 is prime with chance about 2.5 / ln value):

1. run_chance: the Stage 3 chance for every run, at every length.
2. member_chance: the chance that a prime of a given size belongs to each
   constellation, from the Hardy-Littlewood prime-density formula for
   groups of primes. Exact shares are used for primes of up to 7 digits.
3. expected_sets: how many sets of a constellation's members would sit
   within W digits of each other if each particular L-digit number turned
   up at any given place with chance 1 in 10^L.
"""
import math
from functools import lru_cache
from itertools import combinations

import numpy as np

from . import primes

LN10 = math.log(10)
SHORT_LIMIT = 7          # exact shares for primes up to this many digits


# ---------------------------------------------------------------- 1. runs

def run_chance(digits, Lmax, lo=1):
    """Chance that each run is prime, as an array q[start, length - 1].

    Runs that start with 0, end in an even digit or 5 (single 2 and 5
    excepted), or pass the end of the stream have chance 0.
    """
    n = len(digits)
    d = np.frombuffer(digits.encode(), dtype=np.uint8) - 48
    lead = np.array([math.log(int(digits[s:s + 17])) - (len(digits[s:s + 17]) - 1) * LN10
                     if digits[s] != "0" else 0.0 for s in range(n)])
    q = np.zeros((n, Lmax))
    starts_ok = d != 0
    for L in range(max(lo, 1), Lmax + 1):
        m = n - L + 1
        if m <= 0:
            break
        last = d[L - 1:]
        if L == 1:
            ok = np.isin(last, (1, 2, 3, 5, 7, 9))
        else:
            ok = np.isin(last, (1, 3, 7, 9))
        ok &= starts_ok[:m]
        if L in primes.SHORT:
            val = np.full(m, primes.SHORT[L])
        else:
            val = 2.5 / ((L - 1) * LN10 + lead[:m])
        q[:m, L - 1] = np.where(ok, val, 0.0)
    return q


# ------------------------------------------------------ 2. constellations

@lru_cache(maxsize=None)
def _small_primes(limit=1_000_000):
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(limit ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(range(p * p, limit + 1, p)))
    return [p for p in range(limit + 1) if sieve[p]]


@lru_cache(maxsize=None)
def singular_series(offsets):
    """Hardy-Littlewood constant for primes at all of the given offsets."""
    H = sorted(set(offsets))
    k = len(H)
    total = 0.0
    for p in _small_primes():
        w = len({h % p for h in H})
        if w == p:
            return 0.0
        total += math.log1p(-w / p) - k * math.log1p(-1 / p)
    return math.exp(total)


def configurations(patterns):
    """Every way a prime can sit in the pattern, as offsets from it."""
    out = set()
    for pat in patterns:
        for q in pat:
            out.add(frozenset(r - q for r in pat))
    return sorted(out, key=sorted)


@lru_cache(maxsize=None)
def _union_terms(name):
    from .constellations import PATTERNS
    configs = configurations(PATTERNS[name])
    terms = []
    for r in range(1, len(configs) + 1):
        for group in combinations(configs, r):
            U = frozenset().union(*group)
            terms.append(((-1) ** (r + 1), len(U) - 1,
                          singular_series(tuple(sorted(U)))))
    return terms


def member_chance_formula(name, ln_p):
    """Chance a prime with natural log ln_p belongs to the constellation."""
    if name == "sophie_germain":
        return singular_series((0, 2)) / (ln_p + math.log(2))
    if name == "safe":
        return singular_series((0, 2)) / (ln_p - math.log(2))
    return sum(sign * c / ln_p ** extra for sign, extra, c in _union_terms(name))


@lru_cache(maxsize=None)
def exact_member_shares():
    """For L = 1..7: share of all L-digit primes in each constellation."""
    from .constellations import MEMBERSHIP, PATTERNS
    limit = 2 * 10 ** SHORT_LIMIT + 40
    sieve = bytearray([1]) * (limit + 1)
    sieve[0:2] = b"\x00\x00"
    for p in range(2, int(limit ** 0.5) + 1):
        if sieve[p]:
            sieve[p * p::p] = bytearray(len(range(p * p, limit + 1, p)))
    pr = lambda v: v >= 0 and sieve[v] == 1
    shares = {}
    for L in range(1, SHORT_LIMIT + 1):
        lo, hi = (1 if L == 1 else 10 ** (L - 1)), 10 ** L
        counts = dict.fromkeys(MEMBERSHIP, 0)
        total = 0
        for p in range(lo, hi):
            if not sieve[p]:
                continue
            total += 1
            for name, pats in PATTERNS.items():
                counts[name] += any(all(pr(p - q + r) for r in pat)
                                    for pat in pats for q in pat)
            counts["sophie_germain"] += pr(2 * p + 1)
            counts["safe"] += p % 2 == 1 and pr((p - 1) // 2)
        shares[L] = {k: c / total for k, c in counts.items()}
    return shares


def member_chance(name, value):
    """Chance that a prime the size of value belongs to the constellation."""
    L = len(str(value))
    if L <= SHORT_LIMIT:
        return exact_member_shares()[L][name]
    return member_chance_formula(name, math.log(value))


# ------------------------------------------------- 3. members side by side

def _merge(known, word):
    """Lay word over known from the same first place; None if they clash."""
    common = min(len(known), len(word))
    if known[:common] != word[:common]:
        return None
    return known if len(known) >= len(word) else word


def expected_sets(members, n, W):
    """Expected number of sets of runs, one per member, within W digits.

    Digits are taken as independent and uniform, so a given L-digit string
    sits at a given place with chance 10^-L. Overlapping runs are handled
    exactly: they must agree where they overlap. Scans the stretch digit
    by digit from the first member's first digit.
    """
    words = [str(m) for m in members]
    k = len(words)
    full = (1 << k) - 1
    total = 0.0
    states = {(0, ""): 1.0}          # (members placed, digits fixed ahead)
    for t in range(W):
        nxt = {}
        for (mask, known), w in states.items():
            free = full & ~mask
            sub = free
            while True:              # every subset of unplaced members
                if t == 0 and sub == 0:
                    pass             # the first place must start a member
                else:
                    merged = known
                    for i in range(k):
                        if sub >> i & 1:
                            merged = _merge(merged, words[i])
                            if merged is None:
                                break
                    if merged is not None:
                        end = t + len(merged)
                        if end <= W:
                            w2 = w * 10.0 ** -(len(merged) - len(known))
                            m2 = mask | sub
                            if m2 == full:
                                total += w2 * max(0, n - end + 1)
                            elif sub or mask:
                                key = (m2, merged[1:])
                                nxt[key] = nxt.get(key, 0.0) + w2
                if sub == 0:
                    break
                sub = (sub - 1) & free
        states = nxt
    return total


def expected_pair_sets(a, b, n, W):
    """expected_sets for two members, by a direct sum over their offset."""
    a, b = str(a), str(b)
    La, Lb = len(a), len(b)
    total = 0.0
    for d in range(La - W, W - Lb + 1):     # start of b minus start of a
        lo, hi = min(0, d), max(La, d + Lb)
        span = hi - lo
        if span > W:
            continue
        if d >= La or d + Lb <= 0:
            p = 10.0 ** -(La + Lb)
        else:                                # overlapping: must agree
            fixed = {}
            ok = True
            for i, c in enumerate(a):
                fixed[i] = c
            for i, c in enumerate(b):
                if fixed.setdefault(d + i, c) != c:
                    ok = False
                    break
            if not ok:
                continue
            p = 10.0 ** -len(fixed)
        total += p * max(0, n - span + 1)
    return total
