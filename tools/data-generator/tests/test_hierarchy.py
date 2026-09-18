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
