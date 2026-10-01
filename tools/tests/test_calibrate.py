"""F7's gate. Run: python3 -m pytest tools/tests -q"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import calibrate as cal


def rows(*specs):
    """(records, seconds) pairs, one row per pair."""
    return [(f"u{i}", r, s) for i, (r, s) in enumerate(specs)]


def cohort(records, seconds, n=5):
    return [(f"u{i}", records, seconds) for i in range(n)]


# --- bands must not cover volumes they never measured ------------------------------------------
#
# The gate passed a sync it should have failed. A 15,732-record sync was graded against band 1,
# which covers under 5,000, came in at 40.1s inside band 1's 14.1..80.0, and passed -- while
# production's own slope puts a sync that size near 153s, outside band 1 entirely.

def test_a_volume_between_the_measured_bands_is_not_graded_by_band():
    band, outside = cal.band_for(15_732)
    assert band is None and outside
    v = cal.judge(15_732, 40.1, band, outside)
    assert v.label == "unbanded" and v.ok
    assert "between Q5's measured bands" in v.detail


def test_the_measured_bands_still_grade_what_they_cover():
    light, _ = cal.band_for(4_000)
    assert light is cal.BANDS[0]
    assert cal.judge(4_000, 20.0, light).label == "ok"
    assert cal.judge(4_000, 9.0, light).label == "FAIL", "below p50 means the model is too light"
    assert cal.judge(4_000, 95.0, light).label == "warn", "above p95 is conservative, not wrong"


def test_the_heavy_band_is_reported_and_not_judged():
    """Its p95 is a pending Q5 re-run. Calling it pass or fail would be inventing the bound."""
    heavy, _ = cal.band_for(70_844)
    assert heavy is cal.BANDS[1]
    assert cal.judge(70_844, 168.6, heavy).label == "ungraded"


# --- the slope is the check that discriminates -------------------------------------------------

def test_the_slope_comes_from_two_cohort_medians():
    got = cal.slope(cohort(10_000, 20.0) + cohort(50_000, 100.0))
    assert got is not None
    ms, lo, hi = got
    assert (lo, hi) == (10_000, 50_000)
    assert ms == (100.0 - 20.0) * 1000 / 40_000   # 2.0 ms/record


def test_a_slope_needs_two_volumes_far_enough_apart():
    """Two points and hope is not a measurement. A field worker and a supervisor is enough."""
    assert cal.slope(cohort(10_000, 20.0)) is None
    assert cal.slope(cohort(10_000, 20.0) + cohort(12_000, 23.0)) is None, "only 1.2x apart"
    # And it does not pass. This asserted `ok` until the day it mattered: a run with one cohort
    # reported success having tested nothing.
    lines, ok = cal.slope_check(cohort(10_000, 20.0))
    assert not ok
    assert "INCONCLUSIVE" in " ".join(lines)


def test_a_slope_four_times_too_fast_fails():
    """The measured case: 2.33 ms/record against production's 8.85."""
    r = cohort(15_732, 40.1) + cohort(70_844, 168.6)
    lines, ok = cal.slope_check(r)
    assert not ok
    text = " ".join(lines)
    assert "2.33 ms/record" in text and "3.8x too fast" in text


def test_the_tolerance_is_a_factor_and_is_symmetric():
    """It was an absolute deviation from a ratio of 1.0, which an under-estimate can never exceed
    however bad: four times too fast scored 0.74 against a 0.75 threshold and only warned."""
    per_record = cal.PRODUCTION_MS_PER_RECORD / 1000

    def check(factor):
        base, span = 10_000, 60_000
        lo = 20.0
        hi = lo + span * per_record * factor
        return cal.slope_check(cohort(base, lo) + cohort(base + span, hi))[1]

    assert check(1.0) and check(1.4), "near production passes"
    assert check(1.9) and check(1 / 1.9), "inside the fail factor warns, either way"
    assert not check(2.5), "too slow fails"
    assert not check(1 / 2.5), "too fast fails by the same margin"


def test_the_gate_fails_when_the_slope_fails_even_though_no_band_did():
    """The whole point. Every band verdict here is unbanded or ungraded -- nothing fails on
    duration -- and the run is still not an instrument."""
    text, ok = cal.report(cohort(15_732, 40.1) + cohort(70_844, 168.6))
    assert not ok
    assert "FAIL --" in text
    assert "FAIL" not in text.split("Marginal cost")[0].replace("FAIL --", ""), \
        "no band verdict failed; the slope is what caught it"


def test_an_unmeasurable_slope_is_inconclusive_not_a_pass():
    """It returned a pass once. With one cohort the band checks cannot fail either -- every
    verdict is unbanded or ungraded -- so the run printed "the simulation reproduces production"
    having tested nothing at all."""
    text, ok = cal.report(cohort(15_732, 40.1))
    assert not ok
    assert "INCONCLUSIVE" in text
    assert "PASS --" not in text and "FAIL --" not in text


def test_an_inconclusive_run_reads_differently_from_a_failing_one():
    bad = cal.report(cohort(15_732, 40.1) + cohort(70_844, 168.6))[0]
    thin = cal.report(cohort(15_732, 40.1))[0]
    assert "FAIL --" in bad and "INCONCLUSIVE" not in bad
    assert "INCONCLUSIVE" in thin and "FAIL --" not in thin
