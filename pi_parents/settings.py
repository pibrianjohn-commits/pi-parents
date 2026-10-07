"""Settings Brian chooses. Each one marked OPEN is still to be confirmed.

Every result file records the settings it was made with.
"""

DECIMAL_PLACES = 10_000

# Entropy window sizes, in digits, each slid one digit at a time.
# Chosen by Brian; every size is run and reported side by side.
ENTROPY_WINDOWS = (3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30, 50)

# Digit streams are decimals only: Parent One's leading "2", Parent Two's
# "0" and pi's "3" are left out. Chosen by Brian.
INCLUDE_LEADING_DIGIT = False

# How many of the lowest-entropy windows to list in the Stage 2 report.
LOWEST_WINDOWS_LISTED = 10

# Stage 3 prime search, chosen by Brian: every run of these lengths from
# every starting digit, skipping runs that start with 0 or end in an even
# digit or 5. Length 1 is the exception: 2, 3, 5 and 7 all count as primes.
# Pass A is fast; pass B is the long one.
PRIME_PASSES = {"A": (1, 100), "B": (101, 1000)}

# Starting digits per saved piece of work. A stopped run resumes from the
# pieces already saved.
PRIME_CHUNK_STARTS = {"A": 500, "B": 50}
