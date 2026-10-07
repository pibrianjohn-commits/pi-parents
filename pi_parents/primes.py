"""Stage 3: prime search along a digit stream.

From every starting digit, each run of the pass's lengths is read as a whole
number and tested for primality. Runs that start with 0, or end in an even
digit or 5, are skipped, except that single digits 2 and 5 are tested, so
that 2, 3, 5 and 7 count as primes at length 1. Every prime found is recorded as
(stream, start place, length), where place 1 is the first decimal.

Primality: a gcd against the product of the primes up to 20,000 throws out
most composites cheaply; the rest go to gmpy2.is_prime (GMP's trial
division, a Baillie-PSW test and one extra Miller-Rabin round). That is
certain below 2^64, and no composite has ever been known to pass it above.

Work is split into pieces of a few dozen starting digits. Each piece is
saved to disk as soon as it is done, so a stopped run carries on from the
pieces already saved.
"""
import csv
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import gmpy2
from gmpy2 import mpz

from . import settings, streams

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results" / "stage3"
TRIAL_BOUND = 20_000
LN10 = math.log(10)

# Primes below 10^k (k = 1..7), for the exact chance figure at short lengths.
PRIMES_BELOW = [0, 4, 25, 168, 1_229, 9_592, 78_498, 664_579]


def chance_short(L):
    """Share of the L-digit runs that get tested which are prime (exact,
    for L up to 7). Single digits tested are 1, 2, 3, 5, 7 and 9; longer
    runs start with 1-9 and end in 1, 3, 7 or 9."""
    if L == 1:
        return 4 / 6
    primes = PRIMES_BELOW[L] - PRIMES_BELOW[L - 1]
    return primes / (9 * 10 ** (L - 2) * 4)


SHORT = {L: chance_short(L) for L in range(1, len(PRIMES_BELOW))}

_primorial = None
_streams = None


def primorial(bound=TRIAL_BOUND):
    """Product of the primes from 3 to bound, leaving out 5."""
    P, p = mpz(1), mpz(2)
    while True:
        p = gmpy2.next_prime(p)
        if p > bound:
            return P
        if p != 5:
            P *= p


def is_prime(v, P):
    if v <= TRIAL_BOUND:
        return gmpy2.is_prime(v)
    return gmpy2.gcd(v, P) == 1 and gmpy2.is_prime(v)


def search(digits, starts, lo, hi, P=None):
    """Primes among the runs of lo..hi digits beginning at the given starts.

    Returns the primes as (start index, length), and for each length how
    many runs were tested and how many primes chance alone would give.
    """
    P = primorial() if P is None else P
    n = len(digits)
    primes, tested, expected = [], {}, {}
    for s in starts:
        if digits[s] == "0":
            continue
        # The run's size, for the chance figure: its first 17 digits
        # fix ln(value) to far better than needed.
        lead = digits[s:s + 17]
        ln_lead = math.log(int(lead)) - (len(lead) - 1) * LN10
        top = min(hi, n - s)
        if top < lo:
            continue
        v = mpz(digits[s:s + lo - 1]) if lo > 1 else mpz(0)
        for L in range(lo, top + 1):
            c = digits[s + L - 1]
            v = v * 10 + (ord(c) - 48)
            if c in ("0468" if L == 1 else "024568"):
                continue
            tested[L] = tested.get(L, 0) + 1
            # A number not divisible by 2 or 5 is prime with chance
            # about 2.5 / ln(value); exact shares for short runs.
            chance = (SHORT[L] if L in SHORT
                      else 2.5 / ((L - 1) * LN10 + ln_lead))
            expected[L] = expected.get(L, 0.0) + chance
            if is_prime(v, P):
                primes.append((s, L))
    return primes, tested, expected


def _init(stream_set):
    global _primorial, _streams
    _primorial, _streams = primorial(), stream_set


def _work(task):
    name, pass_name, first, last, path = task
    lo, hi = settings.PRIME_PASSES[pass_name]
    digits, _ = _streams[name]
    primes, tested, expected = search(digits, range(first, last), lo, hi,
                                      _primorial)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(dict(primes=primes, tested=tested,
                                   expected=expected)))
    os.replace(tmp, path)            # a piece is either whole or absent
    return name, pass_name


def out_dir(tag=None):
    tag = f"D{settings.DECIMAL_PLACES}" if tag is None else tag
    return RESULTS_DIR / tag


def tasks_for(stream_set, passes, base):
    todo, total = [], 0
    for pass_name in passes:
        size = settings.PRIME_CHUNK_STARTS[pass_name]
        for name, (digits, _) in stream_set.items():
            piece_dir = base / f"pieces_pass_{pass_name}" / name
            piece_dir.mkdir(parents=True, exist_ok=True)
            for first in range(0, len(digits), size):
                total += 1
                path = piece_dir / f"{first:06d}.json"
                if not path.exists():
                    todo.append((name, pass_name, first,
                                 min(first + size, len(digits)), path))
    return todo, total


def merge(stream_set, pass_name, base):
    """Join a finished pass's pieces into one prime list and a summary.

    Streams are written one at a time, so a few hundred controls never
    have to sit in memory together.
    """
    lo, hi = settings.PRIME_PASSES[pass_name]
    summary = dict(
        settings=dict(decimal_places=settings.DECIMAL_PLACES,
                      include_leading_digit=settings.INCLUDE_LEADING_DIGIT,
                      pass_name=pass_name, shortest=lo, longest=hi,
                      trial_bound=TRIAL_BOUND,
                      test="gcd with primorial, then gmpy2.is_prime"),
        streams={})
    with open(base / f"primes_pass_{pass_name}.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stream", "start_place", "length"])
        for name, (digits, first_place) in sorted(stream_set.items()):
            piece_dir = base / f"pieces_pass_{pass_name}" / name
            rows, tested, expected, found = [], {}, {}, {}
            for path in sorted(piece_dir.glob("*.json")):
                piece = json.loads(path.read_text())
                for s, L in piece["primes"]:
                    rows.append((name, first_place + s, L))
                    found[L] = found.get(L, 0) + 1
                for L, c in piece["tested"].items():
                    tested[int(L)] = tested.get(int(L), 0) + c
                for L, x in piece["expected"].items():
                    expected[int(L)] = expected.get(int(L), 0.0) + x
            w.writerows(sorted(rows))
            summary["streams"][name] = dict(
                primes=sum(found.values()), tested=sum(tested.values()),
                expected=sum(expected.values()),
                by_length={L: dict(primes=found.get(L, 0),
                                   tested=tested.get(L, 0),
                                   expected=round(expected.get(L, 0.0), 3))
                           for L in range(lo, hi + 1)})
    (base / f"summary_pass_{pass_name}.json").write_text(
        json.dumps(summary, indent=1) + "\n")
    return summary


def run(passes=("A", "B"), stream_set=None, tag=None, cores=None):
    if stream_set is None:
        stream_set = streams.load_streams()
    base = out_dir(tag)
    todo, total = tasks_for(stream_set, passes, base)
    log = open(base / "progress.log", "a")

    def note(msg):
        line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    note(f"passes {''.join(passes)}: {total - len(todo)} of {total} pieces "
         f"already saved, {len(todo)} to do, on {cores or os.cpu_count()} cores")
    left = {p: sum(1 for t in todo if t[1] == p) for p in passes}
    done, t0 = 0, time.time()
    with Pool(cores, initializer=_init, initargs=(stream_set,)) as pool:
        for name, pass_name in pool.imap_unordered(_work, todo):
            done += 1
            left[pass_name] -= 1
            if done % 25 == 0 or done == len(todo):
                rate = (time.time() - t0) / done
                note(f"{done} of {len(todo)} pieces done, about "
                     f"{rate * (len(todo) - done) / 60:.0f} min to go")
            if left[pass_name] == 0:
                merge(stream_set, pass_name, base)
                note(f"pass {pass_name} complete and merged")
    for pass_name in passes:         # nothing was left to do
        if not (base / f"summary_pass_{pass_name}.json").exists():
            merge(stream_set, pass_name, base)
    log.close()
    return base


if __name__ == "__main__":
    passes = tuple(sys.argv[1]) if len(sys.argv) > 1 else ("A", "B")
    run(passes)
