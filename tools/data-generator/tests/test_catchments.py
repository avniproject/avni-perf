import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import catchments as cat
import hierarchy as hy

PILOT_VILLAGES = 167


def pilot():
    h = hy.build(1, PILOT_VILLAGES)
    return h, *cat.plan(h)


def test_the_pilot_tenant_lands_on_e6s_numbers():
    """The test scenarios specify 500 field workers and 62 supervisors for a pilot state tenant."""
    _, _, users = pilot()
    fw = [u for u in users if u.role == cat.FIELD_WORKER]
    sv = [u for u in users if u.role == cat.SUPERVISOR]
    assert abs(len(fw) - 500) <= 5
    assert abs(len(sv) - 62) <= 5


def test_field_workers_in_a_village_share_its_catchment():
    """The scenarios: three ASHAs to a village, all pulling the same rows. Not one catchment each."""
    _, _, users = pilot()
    per_catchment = Counter(u.catchment_id for u in users if u.role == cat.FIELD_WORKER)
    assert set(per_catchment.values()) == {3}


def test_a_supervisor_has_a_catchment_to_itself():
    _, _, users = pilot()
    per_catchment = Counter(u.catchment_id for u in users if u.role == cat.SUPERVISOR)
    assert set(per_catchment.values()) == {1}


def test_the_supervisor_ratio_matches_the_establishment():
    _, _, users = pilot()
    fw = sum(1 for u in users if u.role == cat.FIELD_WORKER)
    sv = sum(1 for u in users if u.role == cat.SUPERVISOR)
    assert 7 <= fw / sv <= 9


def test_a_supervisor_catchment_expands_wider_than_a_field_workers():
    """A catchment is declared against one location and the server expands it downward, so a
    sub-centre resolves to its villages while a village resolves to itself."""
    h, cs, _ = pilot()
    fw = next(c for c in cs if c.role == cat.FIELD_WORKER)
    sv = next(c for c in cs if c.role == cat.SUPERVISOR)
    assert len(cat.expanded_locations(h, fw)) == 1
    assert len(cat.expanded_locations(h, sv)) > len(cat.expanded_locations(h, fw))


def test_a_mapping_row_is_written_per_declared_location():
    """catchment_address_mapping is a many-to-many and real configuration uses it — the bundles
    examined for this work carry catchments of three locations each."""
    _, cs, _ = pilot()
    rows = cat.declared_mappings(cs)
    assert len(rows) == sum(len(c.locations) for c in cs)
    assert {r["addresslevel_id"] for r in rows} == {l.id for c in cs for l in c.locations}


def test_descendants_are_never_written_as_declared_rows():
    """The server derives the expanded set itself, so writing descendants would duplicate it."""
    h, cs, _ = pilot()
    sv = next(c for c in cs if c.role == cat.SUPERVISOR)
    declared = {r["addresslevel_id"] for r in cat.declared_mappings([sv])}
    assert declared == {l.id for l in sv.locations}
    assert len(declared) < len(cat.expanded_locations(h, sv))


def test_a_catchment_may_declare_several_locations():
    h = hy.build(1, 20)
    cs, _ = cat.plan(h, declare_leaves=True)
    sv = next(c for c in cs if c.role == cat.SUPERVISOR)
    assert len(sv.locations) > 1


def test_declaring_leaves_reaches_the_same_villages():
    """Declaring a sub-centre also includes the sub-centre itself, so the expanded sets differ by
    that one row. The villages — which is where subjects live — are the same either way."""
    h = hy.build(1, 167)
    anc, _ = cat.plan(h, declare_leaves=False)
    lea, _ = cat.plan(h, declare_leaves=True)
    a = next(c for c in anc if c.role == cat.SUPERVISOR)
    b = next(c for c in lea if c.role == cat.SUPERVISOR)
    leaf = h.levels[-1].name
    villages = lambda c: {l.id for l in cat.expanded_locations(h, c) if l.level_name == leaf}
    assert villages(a) == villages(b)
    assert len(cat.declared_mappings(anc)) < len(cat.declared_mappings(lea))


def test_a_catchment_with_no_locations_is_rejected():
    h = hy.build(1, 5)
    with pytest.raises(ValueError, match="declares no locations"):
        cat.CatchmentSpec(id=1, uuid="c", name="empty", organisation_id=1,
                          locations=(), role=cat.FIELD_WORKER)


def test_every_user_points_at_a_catchment_that_exists():
    _, cs, users = pilot()
    ids = {c.id for c in cs}
    assert all(u.catchment_id in ids for u in users)


def test_device_ids_are_unique_and_stable():
    """D1 branches on deviceId in filterChangedEntities, and G5 requires one per user."""
    _, _, users = pilot()
    assert len({u.device_id for u in users}) == len(users)
    _, _, again = pilot()
    assert [u.device_id for u in again] == [u.device_id for u in users]


def test_usernames_are_unique():
    _, _, users = pilot()
    assert len({u.username for u in users}) == len(users)


def test_feeder_rows_carry_what_the_simulation_reads():
    _, _, users = pilot()
    row = cat.feeder_rows(users)[0]
    assert set(row) == {"userName", "deviceId", "role"}


def test_an_unknown_supervisor_level_is_rejected():
    h = hy.build(1, 20)
    with pytest.raises(ValueError, match="no level named"):
        cat.plan(h, supervisor_level="Ward")


def test_worker_density_is_a_parameter():
    h = hy.build(1, 20)
    _, users = cat.plan(h, field_workers_per_leaf=10)
    per = Counter(u.catchment_id for u in users if u.role == cat.FIELD_WORKER)
    assert set(per.values()) == {10}


def test_ids_can_be_offset_for_a_second_tenant():
    a = hy.build(1, 20, first_id=1)
    b = hy.build(2, 20, first_id=1000)
    ca, ua = cat.plan(a, first_catchment_id=1, first_user_id=1)
    cb, ub = cat.plan(b, first_catchment_id=500, first_user_id=500)
    assert not ({c.id for c in ca} & {c.id for c in cb})
    assert not ({u.id for u in ua} & {u.id for u in ub})
