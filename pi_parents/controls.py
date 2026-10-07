"""Random control streams.

Each control is a stream of uniformly random decimal digits, the same
length as the parents. Stream i is made from a fixed seed, so every
control can be remade exactly and nothing needs storing.
"""
import random
import sys

from . import primes, settings

# Brian's numbers: a few hundred controls for the fast tests, about 20 for
# the long prime pass.
CONTROLS_FAST = 400
CONTROLS_SLOW = 20
TAG = "controls"


def name(i):
    return f"random_{i:03d}"


def random_stream(i, D=None):
    D = settings.DECIMAL_PLACES if D is None else D
    rng = random.Random(f"pi-parents control {i}")
    return "".join(rng.choices("0123456789", k=D))


def control_set(count, D=None):
    """count controls, as name -> (digits, first place)."""
    return {name(i): (random_stream(i, D), 1) for i in range(1, count + 1)}


def run_primes(passes="AB"):
    """Pass A on every control, pass B on the first CONTROLS_SLOW."""
    if "A" in passes:
        primes.run(("A",), control_set(CONTROLS_FAST), TAG)
    if "B" in passes:
        primes.run(("B",), control_set(CONTROLS_SLOW), TAG)


if __name__ == "__main__":
    run_primes(sys.argv[1] if len(sys.argv) > 1 else "AB")
