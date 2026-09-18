import random, statistics, sys, tempfile
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import bundle as bundle_mod
import fixture
import profile as profile_mod
import rows
from distribution import Quantiles
from observations import KeyCount

REFERENCE = date(2026, 9, 18)


def context():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    b = bundle_mod.load(d)
    prof = profile_mod.load()
    st = rows.SubjectTypeRef(id=1, uuid=fixture.SUBJECT_TYPE, name="Person",
                             sync_concept_1=fixture.CODED)
    clocks = {t: rows.Clock(reference=REFERENCE, age_days=ts.age_days,
                            edited_fraction=ts.edited_after_creation_fraction,
                            median_days_to_first_edit=ts.median_days_to_first_edit)
              for t, ts in prof.temporal.items()}
    return rows.Context(
        bundle=b, organisation_id=42, subject_types=[st],
        programs=[rows.ProgramRef(id=7, uuid="prog-1", name="Programme")],
        encounter_types=[rows.EncounterTypeRef(id=9, uuid="et-1", name="Visit")],
        clocks=clocks,
        key_counts={ft: t.key_count for ft, t in prof.targets.items()},
        reference=REFERENCE,
    ), st


def catchment():
    return rows.Catchment(user_id=1, address_ids=(101, 102, 103))


# --- timestamps -------------------------------------------------------------

def test_modified_age_reproduces_the_measured_percentiles():
    """Q14 measured the age of last_modified, so that is what has to come back out."""
    ts = profile_mod.load().temporal_for("program_encounter")
    clock = rows.Clock(reference=REFERENCE, age_days=ts.age_days,
                       edited_fraction=ts.edited_after_creation_fraction,
                       median_days_to_first_edit=ts.median_days_to_first_edit)
    rng = random.Random(5)
    ages = sorted((REFERENCE - clock.created_and_modified(rng)[1].date()).days
                  for _ in range(40_000))
    assert abs(statistics.median(ages) - 698) <= 698 * 0.05
    assert abs(ages[int(0.9 * len(ages))] - 1897) <= 1897 * 0.05


def test_creation_precedes_modification_and_the_edit_rate_matches():
    ts = profile_mod.load().temporal_for("program_encounter")
    clock = rows.Clock(reference=REFERENCE, age_days=ts.age_days,
                       edited_fraction=ts.edited_after_creation_fraction,
                       median_days_to_first_edit=ts.median_days_to_first_edit)
    rng = random.Random(9)
    pairs = [clock.created_and_modified(rng) for _ in range(20_000)]
    assert all(c <= m for c, m in pairs)
    edited = [(c, m) for c, m in pairs if m > c]
    assert abs(len(edited) / len(pairs) - 0.748) < 0.02
    gaps = sorted((m - c).days for c, m in edited)
    assert abs(statistics.median(gaps) - 32) <= 6


def test_tables_get_their_own_spread():
    """Program encounters are edited far more often, and far sooner, than subjects."""
    prof = profile_mod.load()
    pe, ind = prof.temporal_for("program_encounter"), prof.temporal_for("individual")
    assert pe.edited_after_creation_fraction > ind.edited_after_creation_fraction
    assert pe.median_days_to_first_edit < ind.median_days_to_first_edit / 10


def test_timestamps_never_land_in_the_future():
    ts = profile_mod.load().temporal_for("encounter")
    clock = rows.Clock(reference=REFERENCE, age_days=ts.age_days,
                       edited_fraction=ts.edited_after_creation_fraction,
                       median_days_to_first_edit=ts.median_days_to_first_edit)
    rng = random.Random(3)
    assert all(m.date() <= REFERENCE for _, m in
               (clock.created_and_modified(rng) for _ in range(5000)))


def test_a_table_with_no_configured_spread_fails_loudly():
    ctx, st = context()
    ctx.clocks.pop("individual")
    with pytest.raises(KeyError, match="individual"):
        rows.individual(ctx, catchment(), st, random.Random(1))


# --- rows -------------------------------------------------------------------

def test_subject_carries_the_audit_and_tenant_columns():
    ctx, st = context()
    r = rows.individual(ctx, catchment(), st, random.Random(1))
    assert r["organisation_id"] == 42
    assert r["subject_type_id"] == 1
    assert r["address_id"] in catchment().address_ids
    assert r["is_voided"] is False
    assert r["uuid"] and r["version"] == 0


def test_sync_concept_value_is_denormalised_from_the_subjects_own_observation():
    """sync_3 and sync_4 index these columns. Leaving them null means never touching those paths."""
    ctx, st = context()
    rng = random.Random(2)
    filled = [rows.individual(ctx, catchment(), st, rng) for _ in range(200)]
    matched = [r for r in filled if r["sync_concept_1_value"] is not None]
    assert matched, "the designated sync concept was never populated"
    for r in matched:
        observed = r["observations"][fixture.CODED]
        expected = observed if isinstance(observed, str) else (
            observed[0] if len(observed) == 1 else None)
        if expected is not None:
            assert r["sync_concept_1_value"] == expected


def test_a_single_valued_answer_is_stored_as_a_scalar_not_a_list():
    """ObservationCollection.getAsSingleStringValue collapses a one-entry array to its entry.
    Storing a list repr would put a value in the column no sync query can match."""
    st = rows.SubjectTypeRef(id=1, uuid="s", name="P", sync_concept_1="c1")
    assert rows._sync_values(st, {"c1": ["only"]})["sync_concept_1_value"] == "only"
    assert rows._sync_values(st, {"c1": "plain"})["sync_concept_1_value"] == "plain"
    multi = rows._sync_values(st, {"c1": ["a", "b"]})["sync_concept_1_value"]
    assert multi == '["a", "b"]' and "'" not in multi


def test_no_sync_value_when_the_subject_type_designates_none():
    ctx, _ = context()
    plain = rows.SubjectTypeRef(id=2, uuid=fixture.SUBJECT_TYPE, name="Plain")
    r = rows.individual(ctx, catchment(), plain, random.Random(1))
    assert r["sync_concept_1_value"] is None and r["sync_concept_2_value"] is None


def test_enrolment_inherits_address_and_sync_values_from_its_subject():
    ctx, st = context()
    rng = random.Random(4)
    subject = rows.individual(ctx, catchment(), st, rng) | {"id": 555}
    e = rows.program_enrolment(ctx, subject, ctx.programs[0], rng)
    assert e["individual_id"] == 555
    assert e["address_id"] == subject["address_id"]
    assert e["sync_concept_1_value"] == subject["sync_concept_1_value"]


def test_a_child_row_never_predates_its_parent():
    ctx, st = context()
    rng = random.Random(6)
    for _ in range(300):
        subject = rows.individual(ctx, catchment(), st, rng) | {"id": 1}
        enrolment = rows.program_enrolment(ctx, subject, ctx.programs[0], rng) | {"id": 2}
        pe = rows.program_encounter(ctx, enrolment, ctx.encounter_types[0], rng)
        enc = rows.encounter(ctx, subject, ctx.encounter_types[0], rng)
        assert enrolment["created_date_time"] >= subject["created_date_time"]
        assert pe["created_date_time"] >= enrolment["enrolment_date_time"]
        assert enc["created_date_time"] >= subject["created_date_time"]


def test_program_encounter_denormalises_both_parents():
    ctx, st = context()
    rng = random.Random(8)
    subject = rows.individual(ctx, catchment(), st, rng) | {"id": 11}
    enrolment = rows.program_enrolment(ctx, subject, ctx.programs[0], rng) | {"id": 22}
    pe = rows.program_encounter(ctx, enrolment, ctx.encounter_types[0], rng)
    assert (pe["program_enrolment_id"], pe["individual_id"]) == (22, 11)
    assert pe["address_id"] == subject["address_id"]


def test_uuids_are_unique_across_rows():
    ctx, st = context()
    rng = random.Random(10)
    seen = {rows.individual(ctx, catchment(), st, rng)["uuid"] for _ in range(2000)}
    assert len(seen) == 2000


def test_a_form_type_absent_from_the_bundle_yields_empty_observations():
    """The fixture has only an IndividualProfile mapping, so encounters have nothing to fill."""
    ctx, st = context()
    rng = random.Random(12)
    subject = rows.individual(ctx, catchment(), st, rng) | {"id": 1}
    assert rows.encounter(ctx, subject, ctx.encounter_types[0], rng)["observations"] == {}


def test_generation_is_reproducible_for_a_seed():
    ctx, st = context()
    a = [rows.individual(ctx, catchment(), st, random.Random(77))["observations"] for _ in range(10)]
    b = [rows.individual(ctx, catchment(), st, random.Random(77))["observations"] for _ in range(10)]
    assert a == b
