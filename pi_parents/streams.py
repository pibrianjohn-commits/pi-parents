"""Turning the saved numbers into the digit streams the analysis reads."""
from . import parents, settings

STREAM_NAMES = {"parent_one": "Parent One", "parent_two": "Parent Two",
                "pi": "Pi"}


def digit_stream(decimal, include_leading_digit):
    """The digits to analyse, plus the decimal place of the first digit.

    A leading "0" (Parent Two) is never part of the stream. Place 0 means
    the whole-number digit, place 1 the first decimal.
    """
    whole, frac = decimal.split(".")
    if include_leading_digit and whole != "0":
        return whole + frac, 1 - len(whole)
    return frac, 1


def load_streams(D=None, include_leading_digit=None):
    D = settings.DECIMAL_PLACES if D is None else D
    if include_leading_digit is None:
        include_leading_digit = settings.INCLUDE_LEADING_DIGIT
    numbers = parents.load(D)
    return {name: digit_stream(numbers[name], include_leading_digit)
            for name in STREAM_NAMES}
