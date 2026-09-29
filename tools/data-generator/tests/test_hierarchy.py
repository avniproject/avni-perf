import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import hierarchy as hy


def test_leaf_count_is_exact():
    """The leaf count sets worker count, beneficiary count and encounter volume, so it cannot drift.
    Scaling a state's 59,000 villages downward would land wherever the rounding fell."""
    for n in (1, 21, 167, 502, 1000):
        assert len(hy.build(1, n).leaves) == n


def test_the_deployment_hierarchy_is_six_levels():
    """Q13 measured production at four levels for 84% of locations. This is two deeper, and
    lineage is an ltree that catchment resolution and RLS ancestor lookups both walk."""
    h = hy.build(1, 167)
    assert [s.name for s in h.levels] == \
        ["State", "District", "Block", "PHC", "Sub-Centre", "Village"]
    assert max(l.depth for l in h.locations) == 6


def test_villages_per_sub_centre_matches_the_establishment():
    h = hy.build(1, 167)
    ratio = len(h.leaves) / len(h.at("Sub-Centre"))
    assert 2.5 <= ratio <= 3.1, ratio


def test_lineage_is_a_root_to_leaf_path_of_ids():
    h = hy.build(1, 167)
    leaf = h.leaves[0]
    path = h.lineage(leaf).split(".")
    assert len(path) == leaf.depth
    assert path[-1] == str(leaf.id)
    assert path[0] == str(h.at("State")[0].id)


def test_every_location_has_a_lineage_as_deep_as_its_level():
    h = hy.build(1, 167)
    for l in h.locations:
        assert len(h.lineage(l).split(".")) == l.depth


def test_only_the_root_has_no_parent():
    h = hy.build(1, 167)
    rootless = [l for l in h.locations if l.parent_id is None]
    assert len(rootless) == 1 and rootless[0].level_name == "State"


def test_a_sub_centres_descendants_are_its_villages():
    h = hy.build(1, 167)
    sc = h.at("Sub-Centre")[0]
    kids = h.descendants(sc)
    assert kids and all(k.level_name == "Village" for k in kids)


def test_ancestors_walks_up_to_the_named_level():
    h = hy.build(1, 167)
    leaf = h.leaves[0]
    assert h.ancestors(leaf, "Sub-Centre").level_name == "Sub-Centre"
    assert h.ancestors(leaf, "State") is h.at("State")[0]
    assert h.ancestors(leaf, "Village") is leaf


def test_children_are_spread_rather_than_filling_each_parent_in_turn():
    """Filling parents in order leaves the last one holding every remainder, which makes one
    catchment far larger than the rest and skews the load for no reason in the data."""
    h = hy.build(1, 167)
    per_parent = Counter(l.parent_id for l in h.leaves)
    assert max(per_parent.values()) - min(per_parent.values()) <= 1


def test_ids_are_unique_and_offsettable_for_a_second_tenant():
    a = hy.build(1, 20, first_id=1)
    b = hy.build(2, 20, first_id=1000)
    assert not ({l.id for l in a.locations} & {l.id for l in b.locations})


def test_a_leafless_hierarchy_is_rejected():
    with pytest.raises(ValueError, match="at least one"):
        hy.build(1, 0)


def test_lineage_satisfies_the_databases_check_constraint():
    """`lineage_parent_consistency` on address_level:

        (parent_id IS NOT NULL AND SUBLTREE(lineage, 0, NLEVEL(lineage)) ~ '*.<parent_id>.<id>')
        OR (parent_id IS NULL AND lineage ~ '<id>')

    A COPY that violates it is rejected outright, so this is the cheapest possible check that the
    generated tree will load at all.
    """
    h = hy.build(1, 167)
    for l in h.locations:
        path = h.lineage(l).split(".")
        if l.parent_id is None:
            assert path == [str(l.id)], f"{l.title}: root lineage must be its own id"
        else:
            assert path[-2:] == [str(l.parent_id), str(l.id)], \
                f"{l.title}: lineage must end .parent_id.id"


def test_lineage_carries_the_whole_ancestor_chain():
    """The constraint only validates the last two path elements — its own comment says it checks
    the parent-child link and not the whole tree. So a wrong ancestor would load cleanly and give
    catchment expansion the wrong scope, silently. Nothing but the generator guards this."""
    h = hy.build(1, 167)
    by_id = {l.id: l for l in h.locations}
    for l in h.locations:
        path = [int(x) for x in h.lineage(l).split(".")]
        walked, cur = [], l.id
        while cur is not None:
            walked.append(cur)
            cur = by_id[cur].parent_id
        assert path == list(reversed(walked)), f"{l.title}: lineage diverges from its parent chain"


def test_catchment_expansion_matches_what_the_database_view_computes():
    """virtual_catchment_address_mapping_table is a view whose function splits each location's
    lineage and joins every element against catchment_address_mapping — so a location belongs to a
    catchment when any of its lineage points is declared against it. This asserts the generator's
    descendant walk agrees with that lineage-based definition."""
    import catchments as cat
    h = hy.build(1, 167)
    cs, _ = cat.plan(h)
    declared: dict[int, set[int]] = {}
    for row in cat.declared_mappings(cs):
        declared.setdefault(row["catchment_id"], set()).add(row["addresslevel_id"])

    for c in cs[:40]:
        as_view = {l.id for l in h.locations
                   if {int(x) for x in h.lineage(l).split(".")} & declared[c.id]}
        assert {l.id for l in cat.expanded_locations(h, c)} == as_view, c.name


def test_supervisor_span_sets_branching_not_a_ratio():
    """Supervisors are derived from the tree, so the span has to come from the tree.

    `catchments.plan` makes one supervisor per sub-centre. There is no ratio to set anywhere
    else -- the only way to widen a span is to put more villages under each sub-centre.
    """
    est = hy.with_supervisor_span(20, field_workers_per_village=3)
    village = dict((name, b) for name, b in est)["Village"]
    assert village == pytest.approx(20 / 3)
    # Every other level is untouched, so the shape above sub-centre stays the measured one.
    assert dict(est)["Block"] == dict(hy.ESTABLISHMENT)["Block"]


def test_a_span_narrower_than_a_village_is_refused():
    """Below one village per sub-centre there would be more supervisors than villages."""
    with pytest.raises(ValueError, match="villages per sub-centre"):
        hy.with_supervisor_span(2, field_workers_per_village=3)
    with pytest.raises(ValueError, match="must be positive"):
        hy.with_supervisor_span(0, field_workers_per_village=3)


# --- registration location types --------------------------------------------------------------
#
# The defect these cover cost a day. Tanuh's organisation_config restricts Patient registration to
# Village through `customRegistrationLocations`, while its location hierarchy continues one level
# further to Health Center. The generator built down to the deepest type, so every subject and
# every catchment sat below what the configuration permits.
#
# Nothing failed. The rows loaded, the foreign keys held, privileges resolved, and 10,800
# encounters synced. But `AddressLevelService` intersects the user's catchment with the permitted
# types, and `OperatingIndividualScopeAwareRepository` turns an empty intersection into
# `id = 0` -- a hard match-nothing -- so `Individual`, `SubjectMigration`,
# `SubjectProgramEligibility` and `IndividualRelationship` were added by
# `getAllSyncableItems` and then silently dropped by `filterChangedEntities`.

TANUH_TYPES = [
    {"id": 11, "name": "State", "parent_id": None, "uuid": "u-state"},
    {"id": 12, "name": "District", "parent_id": 11, "uuid": "u-district"},
    {"id": 13, "name": "Taluka", "parent_id": 12, "uuid": "u-taluka"},
    {"id": 14, "name": "Village", "parent_id": 13, "uuid": "u-village"},
    {"id": 15, "name": "Health Center", "parent_id": 14, "uuid": "u-hc"},
]


def test_without_a_restriction_the_chain_runs_to_the_deepest_type():
    names = [n for n, _ in hy.from_target_types(TANUH_TYPES)[0]]
    assert names[-1] == "Health Center"


def test_a_restriction_truncates_the_chain_there():
    """So that `hierarchy.leaves` -- which is both where subjects are registered and what
    field-worker catchments are built from -- lands on a permitted type."""
    est, type_ids = hy.from_target_types(TANUH_TYPES, registration_type_ids=[14])
    assert [n for n, _ in est] == ["State", "District", "Taluka", "Village"]
    assert "Health Center" not in type_ids


def test_subjects_and_catchments_move_together():
    """Registering at an ancestor instead of truncating would collapse three catchments into one.

    Matching is on `address_id IN (...)` directly rather than on lineage, so both sides have to
    land on the same rows, and the leaf count is what drives the row totals.
    """
    est, type_ids = hy.from_target_types(TANUH_TYPES, registration_type_ids=[14])
    h = hy.build(3, leaf_count=3, first_id=1, type_ids=type_ids, establishment=est)
    assert [l.level_name for l in h.leaves] == ["Village"] * 3
    assert {l.type_id for l in h.leaves} == {14}


def test_the_deepest_permitted_type_wins_when_several_are_allowed():
    est, _ = hy.from_target_types(TANUH_TYPES, registration_type_ids=[12, 14])
    assert [n for n, _ in est][-1] == "Village"


def test_a_type_off_the_spine_is_refused_rather_than_ignored():
    """Tanuh really does hang facilities off the middle -- District Hospital at 6.5, Public Health
    Center at 4.5. Registration restricted to one of those cannot be generated into, and silently
    falling back to the deepest type is how this defect happened the first time."""
    types = TANUH_TYPES + [{"id": 18, "name": "Public Health Center", "parent_id": 13,
                            "uuid": "u-phc"}]
    with pytest.raises(ValueError, match="are on the target's main hierarchy"):
        hy.from_target_types(types, registration_type_ids=[18])


def test_an_empty_restriction_means_unrestricted():
    """No entry for the subject type is not the same as an entry naming nothing."""
    assert [n for n, _ in hy.from_target_types(TANUH_TYPES, registration_type_ids=[])[0]][-1] \
        == "Health Center"
