# pi-parents

Splits pi into two "parents" in the ratio of its own continued-fraction
numerator and denominator, then looks for entropy and prime structure in
each parent's digits, always checked against control streams. The full
method and roadmap are in [BRIEF.md](BRIEF.md).

## Where things stand

| Stage | | Status |
|---|---|---|
| 1 | Parents generator | Done. Reproduces every check value. |
| 2 | Entropy profile | Done: windows of 3 to 10, 12, 15, 20, 30 and 50 digits. |
| 3 | Prime search | Done on the parents and pi: pass A (1-100 digits) and pass B (101-1,000 digits). |
| 4 | Structure finder | Done on the saved primes (up to 1,000 digits): towers, overlaps, bridges, covers, constellations, low entropy. |
| 5 | Controls and comparison report | Not started |
| 6 | Launchable app | Not started |
| 7 | 100,000 digits | Started: parents and pi to 100,000 places, pass A (1-30 digits), and the low-entropy lean re-tested. |

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
- `data/*_100000.txt`: Parent One = pi^2/(pi+1), Parent Two = pi/(pi+1) and
  pi to 100,000 places. The first 10,000 places match the files above.
- `results/stage4/D100000/lean_report.txt`: Parent One's low-entropy lean
  re-tested at 100,000 places, with ten 10,000-digit blocks for the spread.
- `results/stage4/D10000/report.txt`: Stage 4 in plain tables, Parent One,
  Parent Two and pi side by side, each against prime density's prediction.
  `towers_*.csv` lists every prime with its depth, prime prefixes, prime
  suffixes and number of nested primes; `membership_*.csv` gives each
  prime's constellation families. The full nested lists
  (`nested_*.csv.gz`) and close constellation sets (`close_sets_*.csv`) are
  too big for git and are remade by running Stage 4.

## Settings

These are in `pi_parents/settings.py`, and every result records the settings
that made it.

Decided:

- Entropy windows of 3, 4, 5, 6, 7, 8, 9, 10, 12, 15, 20, 30 and 50 digits, each sliding one digit
  at a time, on Parent One, Parent Two and pi, all reported side by side.
  (The page covers the first six sizes only; no new pages are made.)
- No random control streams for now: the parents are compared with pi and
  with what prime density predicts. The pieces of a stopped random run
  (pass A on 400 random streams, about 86% done) are kept on disk.
- Digit streams are decimals only: Parent One's leading "2", Parent Two's "0"
  and pi's "3" are left out.
- Prime search in two passes, every run from every starting digit: pass A
  1-100 digits (also for a few hundred random streams later), pass B
  101-1,000 digits (also for about 20 random streams later). Runs that start
  with 0 or end in an even digit or 5 are skipped, except at length 1, where
  2, 3, 5 and 7 all count as primes.
- Results are reported in plain English with the key numbers; no more web
  pages or charts.

- Constellations, two tests: (a) which families each prime belongs to as a
  number (twin, cousin, sexy, Sophie Germain and its safe-prime partner,
  triplet, quadruplet, quintuplet, sextuplet); (b) every member appearing
  as a run within 20, 50 or 100 digits.
- Expected counts come from prime density (the Stage 3 chance, extended
  with the Hardy-Littlewood factors for groups of primes) and, for
  constellation sets, from each L-digit number turning up at a place one
  time in 10^L.

Working definitions, open to change:

- Giant: a prime of 101 digits or more (Pass B). Brian's named giants
  (G1700, G1730, M2050, S1400) are longer than the 1,000-digit search, so
  they are checked directly rather than found.
- Prefix, suffix and nested are separate: same first digit, same last digit,
  or strictly inside touching neither end. Depth counts any of the three.
- Low-entropy digits: those inside the lowest-entropy windows, taking as many
  of the lowest values as stay within 5% of windows.

## For whoever works on the code

Python 3 with gmpy2 (`pip install -r requirements.txt`).

```sh
python3 -m pi_parents.parents          # Stage 1: regenerate data/
python3 -m pi_parents.entropy [SIZES..] # Stage 2: entropy profiles into results/
python3 -m pi_parents.primes [A|B|AB]  # Stage 3: prime search, all cores, resumes if stopped
python3 -m pi_parents.structure        # Stage 4: towers, overlaps, bridges, covers, low entropy
python3 -m pi_parents.constellations   # Stage 4: constellation tests (a) and (b)
python3 -m pi_parents.report           # Stage 4: plain-text report
python3 -m pi_parents.lean             # low-entropy lean at 10,000 and 100,000 places
python3 -m unittest discover -s tests -t .
```
