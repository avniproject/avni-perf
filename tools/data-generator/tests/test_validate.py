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
