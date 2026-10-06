"""Settings Brian chooses. Each one marked OPEN is still to be confirmed.

The values here are starting points only. Every result file records the
settings it was made with.
"""

DECIMAL_PLACES = 10_000

# OPEN: entropy window size, in digits. 50 is the first-pass value.
ENTROPY_WINDOW = 50

# OPEN: does Parent One's digit stream start with its leading "2", or only
# with its decimals? The same choice applies to pi's leading "3".
# Parent Two's leading "0" is never included.
INCLUDE_LEADING_DIGIT = False

# How many of the lowest-entropy windows to list in the Stage 2 report.
LOWEST_WINDOWS_LISTED = 10
