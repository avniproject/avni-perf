import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import co_tenants as ct


def planned():
    return ct.plan(days=180)


# --- the shape Q12 measured ------------------------------------------------

def test_the_organisation_count_and_empty_share_match_q12():
    c = planned()
    assert len(c) == 986
    assert sum(1 for x in c if x.empty) == 473


@pytest.mark.parametrize("rank,subjects", ct.MEASURED_RANKS)
def test_the_curve_passes_through_every_measured_rank(rank, subjects):
    assert ct.subjects_at_rank(rank) == pytest.approx(subjects, rel=0.01)


@pytest.mark.parametrize("top,share", [(1, 0.21), (5, 0.45), (10, 0.63), (50, 0.91)])
def test_the_skew_reproduces_q12s_shares(top, share):
    """The skew is the point. 986 equal organisations would misrepresent production as badly as
    no co-tenants at all, because multi-tenancy costs scale with what is in the tables."""
    c = planned()
    total = sum(x.subjects for x in c)
    assert abs(sum(x.subjects for x in c[:top]) / total - share) < 0.03


def test_the_total_is_near_what_q12_measured():
    total = sum(x.subjects for x in planned())
    assert 2_400_000 < total < 2_800_000, total


def test_a_power_law_does_not_fit_which_is_why_the_curve_is_interpolated():
    """The exponent between ranks 1 and 10 is 0.84 and between 1 and 156 it is 1.57, so any single
    fitted curve is wrong somewhere. Recorded so nobody replaces the interpolation with a fit."""
    import math
    s1 = ct.subjects_at_rank(1)
    a10 = math.log(s1 / ct.subjects_at_rank(10)) / math.log(10)
    a156 = math.log(s1 / ct.subjects_at_rank(156)) / math.log(156)
    assert a156 - a10 > 0.5


# --- turning them into something generatable -------------------------------

def test_empty_organisations_are_rows_rather_than_generated_tenants():
    """Half of production's tenants hold nothing. They still cost: RLS predicates evaluate against
    the full set and the planner's statistics span it."""
    c = planned()
    specs = ct.as_tenant_specs(c)
    rows = ct.empty_rows(c)
    assert len(specs) == 513
    assert len(rows) == 473
    assert len(specs) + len(rows) == len(c)


def test_subject_counts_survive_the_conversion():
    """Villages hold the organisation's actual subjects rather than a standard 3,000. Production's
    513th organisation holds one subject; a full village would inflate it three thousandfold."""
    c = planned()
    built = sum(t.beneficiaries for t in ct.as_tenant_specs(c))
    planned_total = sum(x.subjects for x in c)
    assert abs(built - planned_total) / planned_total < 0.01


def test_the_smallest_organisations_stay_small():
    specs = ct.as_tenant_specs(planned())
    assert min(t.beneficiaries for t in specs) < 10


def test_the_largest_keeps_its_villages():
    specs = ct.as_tenant_specs(planned())
    biggest = max(specs, key=lambda t: t.beneficiaries)
    assert biggest.villages > 100
    assert biggest.beneficiaries == pytest.approx(570_805, rel=0.01)


def test_encounters_come_from_the_measured_ratio_not_a_daily_rate():
    """Co-tenant history is not modelled — only their weight in the tables — so an explicit count
    replaces the encounters-per-worker-per-day derivation."""
    specs = ct.as_tenant_specs(planned())
    assert all(t.total_encounters is not None for t in specs)
    total_s = sum(t.beneficiaries for t in specs)
    total_e = sum(t.encounters(180) for t in specs)
    assert 1.0 < total_e / total_s < 1.5     # 2.49 per subject, scaled to 180 of 365 days


def test_a_shorter_dataset_holds_proportionally_fewer_encounters():
    assert sum(x.encounters for x in ct.plan(days=60)) < \
           sum(x.encounters for x in ct.plan(days=180))


def test_ids_do_not_collide_with_the_customers_tenants():
    ids = {x.organisation_id for x in planned()}
    assert min(ids) > 10, "the customer's tenants are 1-10"
    assert len(ids) == 986


def test_a_rank_beyond_the_non_empty_set_holds_nothing():
    assert ct.subjects_at_rank(ct.ORGANISATIONS_WITH_SUBJECTS + 1) == 0


def test_rank_zero_is_rejected():
    with pytest.raises(ValueError, match="rank starts at 1"):
        ct.subjects_at_rank(0)
