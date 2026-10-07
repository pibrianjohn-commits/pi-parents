"""Stage 4 report: plain text tables, Parent One, Parent Two and pi side
by side, each with what prime density predicts for that same stream."""
import json
import sys

from . import settings
from .constellations import MEMBERSHIP, SETS, STRETCHES
from .structure import RESULTS_DIR

NAMES = {"parent_one": "Parent One", "parent_two": "Parent Two", "pi": "Pi"}


def _row(label, cells, width=24):
    return f"{label:<{width}}" + "".join(f"{c:>22}" for c in cells)


def _fe(found, expected):
    """found (found / expected)."""
    if expected:
        return f"{found:,.0f} ({found / expected:.3f})"
    return f"{found:,.0f} (-)"


def build(base=None):
    base = base or RESULTS_DIR / f"D{settings.DECIMAL_PLACES}"
    st = json.loads((base / "structure_summary.json").read_text())["streams"]
    co = json.loads((base / "constellations_summary.json").read_text())
    names = list(NAMES)
    head = _row("", [NAMES[n] for n in names])
    out = ["Stage 4 report. Each entry: count found, then (found / expected",
           "from prime density for that same stream). 1.000 = exactly as",
           "density predicts.", ""]

    def section(title, rows):
        out.extend([title, head])
        out.extend(rows)
        out.append("")

    section("Primes found", [
        _row(f"  {band} digits", [_fe(st[n]["primes_by_band"]["observed"][band],
                                      st[n]["primes_by_band"]["expected"][band])
                                  for n in names])
        for band in ("1-100", "101-1000", "1-1000")])

    rows = []
    for key, label in (("prefix_pairs", "prefix pairs"),
                       ("suffix_pairs", "suffix pairs"),
                       ("nested_pairs", "nested pairs"),
                       ("with_prefix", "primes with a prefix"),
                       ("with_suffix", "primes with a suffix"),
                       ("with_prefix_and_suffix", "  ...with both"),
                       ("with_nested", "primes with a nested")):
        rows.append(_row(f"  {label}", [_fe(st[n]["towers"]["observed"][key],
                                            st[n]["towers"]["expected"][key])
                                        for n in names]))
    for kind in ("prefix", "suffix", "nested"):
        for band in ("1-100", "101-1000"):
            b = {n: st[n]["towers_by_outer_band"][kind] for n in names}
            rows.append(_row(f"  {kind}, outer {band}", [
                _fe(b[n]["observed"][band], b[n]["expected"][band]) for n in names]))
    section("Prefixes, suffixes, nesting", rows)

    rows = [_row("  pairs", [_fe(st[n]["overlaps"]["observed"]["pairs"],
                                 st[n]["overlaps"]["expected"]["pairs"]) for n in names])]
    for key, label in (("shared_1_10", "sharing 1-10"),
                       ("shared_11_100", "sharing 11-100"),
                       ("shared_101_999", "sharing 101-999")):
        rows.append(_row(f"  {label}", [_fe(st[n]["overlaps"]["observed"][key],
                                            st[n]["overlaps"]["expected"][key])
                                        for n in names]))
    rows.append(_row("  mean digits shared", [
        f'{st[n]["overlaps"]["observed"]["mean_shared"]:.1f} '
        f'({st[n]["overlaps"]["expected"]["mean_shared"]:.1f})' for n in names]))
    section("Overlaps (expected in brackets for the mean)", rows)

    rows = []
    for band in ("2-30", "1-100", "101-1000", "1-1000"):
        rows.append(_row(f"  mean, {band} digits", [
            f'{st[n]["stack"][band]["observed_mean"]:.2f} '
            f'({st[n]["stack"][band]["expected_mean"]:.2f})' for n in names]))
        rows.append(_row(f"  highest, {band}", [
            f'{st[n]["stack"][band]["observed_max"]:.0f} at {st[n]["stack"][band]["max_at_place"]:,}'
            for n in names]))
    section("Stack height: primes through each digit (expected in brackets)", rows)

    rows = [_row("  deepest tower", [str(st[n]["depth"]["deepest"]) for n in names])]
    rows.append(_row("  tower starts", [
        "{:,}:{}".format(*st[n]["depth"]["chain"][0]) for n in names]))
    for k in (10, 20, 30, 40):
        rows.append(_row(f"  primes at depth >= {k}", [
            f'{sum(v for d, v in st[n]["depth"]["primes_by_depth"].items() if int(d) >= k):,}'
            for n in names]))
    section("Nesting depth (no density figure; compare with pi)", rows)

    rows = []
    for key, label in (("giants", "giants (101+ digits)"),
                       ("meet", "prefix and suffix meet"),
                       ("gap", "prefix and suffix gap"),
                       ("bridged", "  gap bridged"),
                       ("bridges", "  bridging primes"),
                       ("no_prefix", "no prime prefix"),
                       ("no_suffix", "no prime suffix")):
        rows.append(_row(f"  {label}", [f'{st[n]["bridges"][key]:,}' for n in names]))
    for key, label in (("overlapping_pairs", "overlapping giant pairs"),
                       ("pairs_with_cover", "  with a cover"),
                       ("cover_primes", "cover primes")):
        rows.append(_row(f"  {label}", [f'{st[n]["covers"][key]:,}' for n in names]))
    section("Bridges and covers (no density figure; compare with pi)", rows)

    rows = []
    for W in settings.ENTROPY_WINDOWS:
        le = {n: st[n]["low_entropy"][str(W)] for n in names}

        def ratio(n, band):
            r = le[n][f"stack_{band}"]
            return (r["low_observed"] / r["low_expected"]) / (
                r["rest_observed"] / r["rest_expected"])
        rows.append(_row(f"  window {W}", [
            f'{le[n]["share_of_digits"]:.0%} {le[n]["stack_2-30"]["low_observed"]:.1f}'
            f'/{le[n]["stack_2-30"]["rest_observed"]:.1f} {ratio(n, "2-30"):.3f}'
            for n in names]))
    section("Low entropy (lowest-entropy windows, at most 5%). Each entry:\n"
            "share of digits that are low-entropy, stack of 2-30-digit primes\n"
            "low/elsewhere, then that ratio after dividing out density's\n"
            "prediction for the same digits (1.000 = no effect)", rows)

    rows = []
    for k in ["primes"] + MEMBERSHIP:
        for p in ("A", "B"):
            if k == "primes":
                cells = [f'{co["streams"][n]["membership"][p]["primes"]:,}' for n in names]
            else:
                cells = [_fe(co["streams"][n]["membership"][p][k],
                             co["streams"][n]["membership_expected"][p][k]) for n in names]
            rows.append(_row(f"  {k} pass {p}", cells))
    section("Constellations (a): primes belonging to each family as numbers", rows)

    rows = []
    for name in SETS:
        for W in STRETCHES:
            e = co["side_by_side_expected"][name][str(W)]
            rows.append(_row(f"  {name} {W}", [
                _fe(co["streams"][n]["side_by_side"][name][str(W)]["sets"], e["sets"])
                for n in names]))
    section("Constellations (b): sets of all members within W digits\n"
            "(expected: each L-digit number turns up at a place 1 time in 10^L)", rows)

    rows = []
    for name in SETS:
        for W in STRETCHES:
            e = co["side_by_side_expected"][name][str(W)]
            rows.append(_row(f"  {name} {W}", [
                f'{co["streams"][n]["side_by_side"][name][str(W)]["distinct"]:,} '
                f'({e["distinct"]:.1f})' for n in names]))
    section("Constellations (b): different constellations seen (expected)", rows)

    if "known_cases" in st["parent_one"]:
        rows = []
        for case, v in st["parent_one"]["known_cases"].items():
            if "computed" in v:
                rows.append(f"  {case}: computed {v['computed']}, "
                            f"{'matches' if v['matches'] else 'DOES NOT MATCH'}")
            else:
                rows.append(
                    f"  {case} {v['start']}-{v['end']} ({v['length']} digits): "
                    f"{'prime' if v['prime'] else 'NOT PRIME'}; longest saved prime "
                    f"prefix {v['longest_saved_prefix']}, suffix "
                    f"{v['longest_saved_suffix']}; {v['saved_primes_inside']:,} "
                    f"saved primes inside")
        out.extend(["Known cases in Parent One (0-indexed, end exclusive)"] + rows + [""])

    text = "\n".join(out)
    (base / "report.txt").write_text(text + "\n")
    return text


if __name__ == "__main__":
    print(build())
