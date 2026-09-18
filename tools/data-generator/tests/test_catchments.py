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
    """E6 specifies 500 field workers and 62 supervisors for a pilot state tenant."""
    _, _, users = pilot()
    fw = [u for u in users if u.role == cat.FIELD_WORKER]
    sv = [u for u in users if u.role == cat.SUPERVISOR]
    assert abs(len(fw) - 500) <= 5
    assert abs(len(sv) - 62) <= 5


def test_field_workers_in_a_village_share_its_catchment():
    """E0: three ASHAs to a village, all pulling the same rows. Not one catchment each."""
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
    assert len(cat.expanded_locations(h, sv)) > 1


def test_only_the_declared_location_is_written():
    """The server derives the expanded set itself, so writing the descendants would duplicate it."""
    _, cs, _ = pilot()
    rows = cat.declared_mappings(cs)
    assert len(rows) == len(cs)
    assert {r["addresslevel_id"] for r in rows} == {c.root.id for c in cs}


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
