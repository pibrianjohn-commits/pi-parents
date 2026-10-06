"""Settings Brian chooses. Each one marked OPEN is still to be confirmed.

The values here are starting points only. Every result file records the
settings it was made with.
"""

DECIMAL_PLACES = 10_000

# Entropy window sizes, in digits, each slid one digit at a time.
# Chosen by Brian; every size is run and reported side by side.
ENTROPY_WINDOWS = (10, 12, 15, 20, 30, 50)

# OPEN: does Parent One's digit stream start with its leading "2", or only
# with its decimals? The same choice applies to pi's leading "3".
# Parent Two's leading "0" is never included.
INCLUDE_LEADING_DIGIT = False

# How many of the lowest-entropy windows to list in the Stage 2 report.
LOWEST_WINDOWS_LISTED = 10
