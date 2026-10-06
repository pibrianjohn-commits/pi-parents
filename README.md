# pi-parents

Splits pi into two "parents" in the ratio of its own continued-fraction
numerator and denominator, then looks for entropy and prime structure in
each parent's digits, always checked against control streams. The full
method and roadmap are in [BRIEF.md](BRIEF.md).

## Where things stand

| Stage | | Status |
|---|---|---|
| 1 | Parents generator | Done. Reproduces every check value. |
| 2 | Entropy profile | Done: windows of 10, 12, 15, 20, 30 and 50 digits. |
| 3 | Prime search | Done on the parents and pi: pass A (1-100 digits) and pass B (101-1,000 digits). |
| 4 | Structure finder | Not started |
| 5 | Controls and comparison report | Not started |
| 6 | Launchable app | Not started |
| 7 | 100,000 digits | Not started |

## What to look at

- `data/parent_one_10000.txt`, `data/parent_two_10000.txt`, `data/pi_10000.txt`:
  the numbers to 10,000 places.
- `results/stage2/D10000_decimals_only/entropy.html`: the entropy
  profiles at every window size, side by side. Open it in a web browser.
  (No further pages or charts are being built; results are reported in
  plain English.)
- `results/stage3/D10000/primes_pass_A.csv` and `primes_pass_B.csv`: every
  prime found, one per line as stream, start place, length. Place 1 is the
  first decimal. `summary_pass_*.json` has the counts for each length
  against what chance would give.

## Settings

These are in `pi_parents/settings.py`, and every result records the settings
that made it.

Decided:

- Entropy windows of 10, 12, 15, 20, 30 and 50 digits, each sliding one digit
  at a time, on Parent One, Parent Two and pi. The controls get the same sizes
  in Stage 5, and all sizes are reported side by side.
- Digit streams are decimals only: Parent One's leading "2", Parent Two's "0"
  and pi's "3" are left out.
- Prime search in two passes, every run from every starting digit: pass A
  1-100 digits (also for a few hundred random streams later), pass B
  101-1,000 digits (also for about 20 random streams later). Runs that start
  with 0 or end in an even digit or 5 are skipped, except at length 1, where
  2, 3, 5 and 7 all count as primes.
- Results are reported in plain English with the key numbers; no more web
  pages or charts.

Still to confirm:

- What counts as a "constellation" in a digit stream (Stage 4).

## For whoever works on the code

Python 3 with gmpy2 (`pip install -r requirements.txt`).

```sh
python3 -m pi_parents.parents          # Stage 1: regenerate data/
python3 -m pi_parents.entropy [SIZES..] # Stage 2: entropy profiles into results/
python3 -m pi_parents.primes [A|B|AB]  # Stage 3: prime search, all cores, resumes if stopped
python3 -m unittest discover -s tests -t .
```
