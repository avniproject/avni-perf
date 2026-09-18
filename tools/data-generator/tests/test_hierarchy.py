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
