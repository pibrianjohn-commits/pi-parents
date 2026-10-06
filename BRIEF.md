# Project brief

Brian's brief, as given. The method here is not to be changed without asking him.

```text
PROJECT BRIEF: pi-parents

WHO I AM
I'm Brian, a wood carver, not a programmer. You do all the coding. Keep me
out of the terminal wherever possible. The end product should be something
I can launch and use (a local web page / app), not a set of commands.
Do not change the method below without asking me first.

THE METHOD (exactly as I do it)
1. Compute pi to 10,000 decimal places (later 100,000).
2. Find pi's numerator and denominator by CONTINUED FRACTION expansion:
   step through the convergents until the first one whose quotient matches
   pi to all 10,000 places. (Not "digits over a power of ten".)
3. Treat pi's digit string as one whole number and split it in the ratio
   numerator : denominator. Work to 10,002 decimal places (2 guard digits),
   then truncate each part correctly to 10,000.
   - The larger part (2.383...) is PARENT ONE.
   - The smaller part (0.758...) is PARENT TWO.
4. Slide a Shannon entropy window along each parent's digit stream.
5. Prime search: from every starting digit, test rolling windows of
   ever-increasing length for primality. Skip any run that starts with 0
   or ends in an even digit (or 5).
6. Look at where low entropy and prime structure coincide: overlapping
   primes, nested primes, giant primes with prefix and suffix primes,
   overlaps that are themselves overlapped by giant primes (Parent One),
   and prime constellations: sextuplets, quintuplets etc. (Parent Two).

CHECK VALUES (computed already; your build must reproduce these)
- First matching convergent at 10,000 places: the 9,759th.
- Numerator 5,001 digits, starts 32368563035339958784...
- Denominator 5,001 digits, starts 10303233615711916189...
- Parent One = 2.383045660595017093118212694234... ends ...6695841427
- Parent Two = 0.758546992994776145344430689044... ends ...8560534250
- Both parts match exact truncation in all 10,000 places. Truncated parts
  sum to pi minus 1 in the last place (expected, not an error).

STILL TO CONFIRM WITH ME (make these settings, don't guess silently)
- Entropy window size.
- Shortest and longest prime run lengths.
- Whether Parent One's stream includes the leading "2" or only decimals.
- Exact definition of "constellation" in a digit stream.

CONTROLS (essential)
Run the identical pipeline on: many random digit streams of the same
length (aim for several hundred), pi itself, and one or two other
constants. Every result about the parents must be shown against that
spread, e.g. "Parent One beats 395 of 400 random streams".
Sanity check: about 1 in 2,300 thousand-digit numbers is prime, so a
random 10,000-digit stream should hold roughly 3-4 thousand-digit primes
per length. If a parent shows NONE (Parent Two in my old runs), check
the code (e.g. handling of the leading "0.") before believing it.

FIRST-PASS RESULT (50-digit entropy window, prime runs 2-30 digits)
Parent One: low-entropy stretches carry ~13.0 overlapping primes per digit
vs 12.1 average; only 1 of 40 random streams matched that.
Parent Two: no such effect (30 of 40 random streams beat it).
Pi: no effect. Promising, not yet settled.

ROADMAP
Stage 1  Parents generator, verified against the check values.
Stage 2  Entropy profile.
Stage 3  Prime search, fast (gmpy2, multiprocessing, cheap trial division
         first), saving results to disk and able to resume if stopped.
Stage 4  Structure finder: overlaps, nesting, prefix/suffix primes,
         overlaps-of-overlaps, constellations.
Stage 5  Controls and comparison report.
Stage 6  Launchable app: pick digits / settings, press run, see entropy
         plot, prime map, and parents vs controls side by side. Every run
         saved for later comparison.
Stage 7  Scale to 100,000 digits.

Work one stage at a time. At the end of each stage, give me a short
plain-English summary I can paste back to my other Claude.
```
