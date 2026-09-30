import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import profile as profile_mod
import validate
from validate import Verdict

PROFILE = profile_mod.load()


def observed(table="program_encounter", *, rows=1_000_000, gin_per_row=69,
             all_per_row=1722, p50=12, p95=34, mean_bytes=879):
    return {table: {"rows": rows,
                    "gin_observation_bytes": gin_per_row * rows,
                    "all_index_bytes": all_per_row * rows,
                    "obs_keys_p50": p50, "obs_keys_p95": p95, "obs_mean_bytes": mean_bytes}}


def verdict_for(report, name):
    return next(c for c in report.checks if c.name == name).verdict


# --- the check that matters --------------------------------------------------

def test_a_dataset_matching_production_passes():
    r = validate.run(observed(), PROFILE)
    assert r.ok, r.render()
    assert all(c.verdict is Verdict.PASS for c in r.checks), r.render()


def test_a_gin_index_an_order_of_magnitude_light_fails():
    """H5's whole purpose. A generator drawing on too few concepts produces plausible row counts
    and an index that sits in cache, and every push figure then comes out optimistic."""
    r = validate.run(observed(gin_per_row=7), PROFILE)
    assert verdict_for(r, "GIN bytes/row") is Verdict.FAIL
    assert not r.ok


def test_a_gin_index_modestly_off_warns_rather_than_failing():
    r = validate.run(observed(gin_per_row=int(69 * 0.55)), PROFILE)
    assert verdict_for(r, "GIN bytes/row") is Verdict.WARN
    assert r.ok, "a warning must not block a dataset on its own"


def test_a_heavier_than_production_index_also_fails():
    """Too much cardinality is wrong in the other direction — it would make the server look worse
    than it is, which is a different way of not measuring production."""
    r = validate.run(observed(gin_per_row=69 * 3), PROFILE)
    assert verdict_for(r, "GIN bytes/row") is Verdict.FAIL


def test_missing_index_bulk_fails_even_when_gin_is_right():
    """G4 requires the generated dataset to carry production's index definitions. Omitting them
    leaves a cache-resident dataset whatever the observations look like."""
    r = validate.run(observed(all_per_row=200), PROFILE)
    assert verdict_for(r, "index bytes/row") is Verdict.FAIL


# --- the weaker checks, and why they are weaker ------------------------------

def test_a_constant_key_count_passes_the_median_and_fails_the_spread():
    """The failure H3 warns about: a generator emitting exactly 12 keys every time matches the
    median perfectly and builds an index of the wrong shape."""
    r = validate.run(observed(p50=12, p95=12), PROFILE)
    assert verdict_for(r, "obs keys p50") is Verdict.PASS
    assert verdict_for(r, "obs keys p95") is Verdict.FAIL


def test_row_count_checks_the_loader_not_the_shape():
    r = validate.run(observed(rows=1_000_000), PROFILE,
                     expected_rows={"program_encounter": 1_000_000})
    assert verdict_for(r, "row count") is Verdict.PASS
    r = validate.run(observed(rows=900_000), PROFILE,
                     expected_rows={"program_encounter": 1_000_000})
    assert verdict_for(r, "row count") is Verdict.FAIL


# --- behaviour --------------------------------------------------------------

def test_an_unmeasured_statistic_warns_rather_than_passing_quietly():
    o = observed()
    o["program_encounter"]["gin_observation_bytes"] = None
    r = validate.run(o, PROFILE)
    assert verdict_for(r, "GIN bytes/row") is Verdict.WARN
    assert "not measured" in next(c for c in r.checks
                                  if c.name == "GIN bytes/row").detail


def test_every_table_in_the_profile_can_be_validated():
    o = {}
    for t, w in PROFILE.index_weight.items():
        o.update(observed(t, gin_per_row=w.gin_observation_bytes,
                          all_per_row=w.all_index_bytes))
    r = validate.run(o, PROFILE)
    assert {c.table for c in r.checks} == set(PROFILE.index_weight)


def test_the_report_says_what_a_failure_means():
    r = validate.run(observed(gin_per_row=3), PROFILE)
    assert "not usable for measurement" in r.render()


def test_the_report_names_the_profile_it_judged_against():
    assert PROFILE.name in validate.run(observed(), PROFILE).render()


def test_a_table_absent_from_the_profile_produces_no_index_checks():
    r = validate.run({"group_subject": {"rows": 10}}, PROFILE)
    assert not [c for c in r.checks if c.name.endswith("bytes/row")]


# --- waivers -----------------------------------------------------------------------------------
#
# Accepted 30 Sep 2026: the customer's subject payload is lighter than production's average. Three
# `individual` checks fail on that permanently, because Tanuh's registration form has 2 generatable
# elements and no row count changes it.
#
# The danger in accepting a permanent failure is that a gate reporting the same four failures every
# run is a gate nobody reads, and the fifth — the real one — arrives invisible.

def _check(name, table, verdict, observed, expected):
    return validate.Check(name, table, verdict, observed, expected, 0.2, "detail")


def _report(*checks):
    r = validate.Report(profile_name="p")
    r.checks = list(checks)
    return r


WAIVER = [{"check": "obs keys p50", "table": "individual", "observed": 2,
           "reason": "the customer's form has 2 elements"}]


def test_a_waived_failure_stops_failing_but_does_not_become_a_pass():
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.FAIL, 2, 7)), WAIVER)
    assert r.checks[0].verdict is validate.Verdict.WAIVED
    assert r.ok
    assert r.waived and not r.failed
    # The reason replaces the detail, so the output says why rather than restating the failure.
    assert "2 elements" in r.checks[0].detail


def test_the_check_still_runs_and_still_reports_its_number():
    """Waiving is not switching the check off. The ratio stays visible in the rendered output."""
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.FAIL, 2, 7)), WAIVER)
    assert r.checks[0].observed == 2 and r.checks[0].expected == 7
    assert "0.29x" in r.render()


def test_a_waiver_stops_applying_once_the_dataset_drifts_away_from_it():
    """The point of naming the accepted value. Accepting 2 keys is not accepting 6, and a waiver
    that covered any future value would be indistinguishable from deleting the check."""
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.FAIL, 6, 7)), WAIVER)
    assert r.checks[0].verdict is validate.Verdict.FAIL
    assert "WAIVER NO LONGER APPLIES" in r.checks[0].detail
    assert "accepted at 2" in r.checks[0].detail
    assert not r.ok


def test_drift_within_the_band_is_still_covered():
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.FAIL, 2.2, 7)), WAIVER)
    assert r.checks[0].verdict is validate.Verdict.WAIVED


def test_a_waiver_only_touches_the_check_and_table_it_names():
    """An unrelated failure must still fail, which is the whole reason for waiving rather than
    lowering the threshold."""
    r = validate.apply_waivers(_report(
        _check("obs keys p50", "individual", validate.Verdict.FAIL, 2, 7),
        _check("GIN bytes/row", "encounter", validate.Verdict.FAIL, 189, 59),
        _check("obs keys p50", "encounter", validate.Verdict.FAIL, 2, 7),
    ), WAIVER)
    assert [c.verdict for c in r.checks] == [
        validate.Verdict.WAIVED, validate.Verdict.FAIL, validate.Verdict.FAIL]
    assert not r.ok


def test_waivers_do_not_promote_warnings():
    """A warning is not a failure, so there is nothing to accept — and silently upgrading one
    would hide a check on its way to failing."""
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.WARN, 2, 7)), WAIVER)
    assert r.checks[0].verdict is validate.Verdict.WARN


def test_the_verdict_records_what_was_accepted():
    """A blessed dataset should say what was accepted about it, not just that it was blessed."""
    import recipe as rec
    r = validate.apply_waivers(
        _report(_check("obs keys p50", "individual", validate.Verdict.FAIL, 2, 7)), WAIVER)
    doc = rec.verdict_document("tanuh-small", r)
    assert doc["counts"]["waived"] == 1
    assert doc["verdict"] == "pass"
    assert any(c["verdict"] == "waived" for c in doc["checks"])


def test_the_shipped_waiver_file_is_well_formed():
    """It is committed, so a typo in a key silently stops covering the thing it names."""
    import json
    from pathlib import Path
    ws = json.loads((Path(__file__).resolve().parents[1]
                     / "datasets" / "tanuh.waivers.json").read_text())
    assert ws
    seen = set()
    for w in ws:
        assert set(w) == {"check", "table", "reason", "observed"}, w
        # Dated, because a waiver records a judgement someone made on a day, and the value it
        # accepted, so drift un-waives it rather than hiding behind it.
        assert w["reason"].startswith("Accepted "), w
        assert isinstance(w["observed"], (int, float)) and w["observed"] > 0, w
        # One waiver per (check, table): two would mean the second silently never applies.
        key = (w["check"], w["table"])
        assert key not in seen, f"duplicate waiver for {key}"
        seen.add(key)
