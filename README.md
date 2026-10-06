# pi-parents

Splits pi into two "parents" in the ratio of its own continued-fraction
numerator and denominator, then looks for entropy and prime structure in
each parent's digits, always checked against control streams. The full
method and roadmap are in [BRIEF.md](BRIEF.md).

## Where things stand

| Stage | | Status |
|---|---|---|
| 1 | Parents generator | Done. Reproduces every check value. |
| 2 | Entropy profile | Done: windows of 10, 12, 15, 20, 30 and 50 digits. Leading digit still open. |
| 3 | Prime search | Not started |
| 4 | Structure finder | Not started |
| 5 | Controls and comparison report | Not started |
| 6 | Launchable app | Not started |
| 7 | 100,000 digits | Not started |

## What to look at

- `data/parent_one_10000.txt`, `data/parent_two_10000.txt`, `data/pi_10000.txt`:
  the numbers to 10,000 places.
- `results/stage2/D10000_decimals_only/entropy.html`: the entropy
  profiles at every window size, side by side. Open it in a web browser.

## Settings

These are in `pi_parents/settings.py`, and every result records the settings
that made it.

Decided:

- Entropy windows of 10, 12, 15, 20, 30 and 50 digits, each sliding one digit
  at a time, on Parent One, Parent Two and pi. The controls get the same sizes
  in Stage 5, and all sizes are reported side by side.

Still to confirm:

- Whether Parent One's stream starts with its leading "2" (and pi's with its
  "3"): currently decimals only. Parent Two's leading "0" is never included.
- Shortest and longest prime run lengths (Stage 3).
- What counts as a "constellation" in a digit stream (Stage 4).

## For whoever works on the code

Python 3, standard library only so far.

```sh
python3 -m pi_parents.parents          # Stage 1: regenerate data/
python3 -m pi_parents.entropy [SIZES..] # Stage 2: entropy profiles into results/
python3 -m unittest discover -s tests -t .
```
