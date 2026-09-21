"""Build a location hierarchy, and the catchments that sit on it.

The shape comes from the real state establishment in the test scenarios -- State, District, Block, PHC,
Sub-Centre, Village -- scaled down to a tenant's village count. Six levels, where Q13 measured
production at four for 84% of its locations, so a generated tenant's lineage is two levels deeper
than production's typical. That costs more to walk: `address_level.lineage` is an `ltree`, and
catchment scope resolution and reference-table RLS both walk ancestors.

Catchments matter as much as the tree. The scenarios establish that the field workers in a village share its
catchment rather than partitioning it, so three of them pull the same rows. And Q15 found catchment
breadth and per-location data density vary independently in production -- a wide catchment in a
sparse organisation holds almost nothing -- so breadth alone does not set sync volume.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

# Children per parent, measured from the establishment table: 75 districts to a state, 11.3 blocks
# to a district, and so on down to 2.8 villages per sub-centre.
ESTABLISHMENT = (
    ("State", None),
    ("District", 75.0),
    ("Block", 11.3),
    ("PHC", 4.2),
    ("Sub-Centre", 5.8),
    ("Village", 2.8),
)


@dataclass(frozen=True)
class LevelSpec:
    name: str
    # Depth 1 is the root. Matches nlevel(lineage).
    depth: int
    count: int


@dataclass(frozen=True)
class Location:
    id: int
    uuid: str
    title: str
    level_name: str
    depth: int
    parent_id: int | None
    type_id: int
    organisation_id: int

    @property
    def lineage(self) -> str:
        """Placeholder. The real value is a path of ids and is filled in by `Hierarchy.lineage`."""
        raise NotImplementedError("use Hierarchy.lineage(location)")


@dataclass
class Hierarchy:
    organisation_id: int
    levels: tuple[LevelSpec, ...]
    locations: list[Location] = field(default_factory=list)
    _parent: dict[int, int | None] = field(default_factory=dict)

    def at(self, level_name: str) -> list[Location]:
        return [l for l in self.locations if l.level_name == level_name]

    @property
    def leaves(self) -> list[Location]:
        return self.at(self.levels[-1].name)

    def lineage(self, location: Location) -> str:
        """The `ltree` path of ids from root to this location, as Postgres stores it."""
        path, cur = [], location.id
        while cur is not None:
            path.append(cur)
            cur = self._parent.get(cur)
        return ".".join(str(i) for i in reversed(path))

    def ancestors(self, location: Location, level_name: str) -> Location | None:
        by_id = {l.id: l for l in self.locations}
        cur: Location | None = location
        while cur is not None:
            if cur.level_name == level_name:
                return cur
            pid = self._parent.get(cur.id)
            cur = by_id.get(pid) if pid is not None else None
        return None

    def descendants(self, location: Location) -> list[Location]:
        """Every location beneath this one, which is what a catchment expands to."""
        children: dict[int | None, list[Location]] = {}
        for l in self.locations:
            children.setdefault(l.parent_id, []).append(l)
        out, stack = [], list(children.get(location.id, []))
        while stack:
            cur = stack.pop()
            out.append(cur)
            stack.extend(children.get(cur.id, []))
        return out


def plan_levels(leaf_count: int, establishment=ESTABLISHMENT) -> tuple[LevelSpec, ...]:
    """Work upward from a leaf count, dividing by each level's branching factor.

    Going upward rather than downward is what keeps the leaf count exact. Scaling a state's 59,000
    villages down by a ratio would land on whatever the rounding produced, and the leaf count is the
    number that matters -- it sets field worker count, beneficiary count and encounter volume.
    """
    if leaf_count < 1:
        raise ValueError("need at least one leaf location")
    counts = [leaf_count]
    for _, branching in reversed(establishment[1:]):
        counts.append(max(1, round(counts[-1] / branching)))
    counts.reverse()
    return tuple(LevelSpec(name=name, depth=i + 1, count=c)
                 for i, ((name, _), c) in enumerate(zip(establishment, counts)))


def build(organisation_id: int, leaf_count: int, *, first_id: int = 1,
          type_ids: dict[str, int] | None = None,
          establishment=ESTABLISHMENT) -> Hierarchy:
    """Build a tenant's location tree, bottom-count driven."""
    levels = plan_levels(leaf_count, establishment)
    ids = itertools.count(first_id)
    h = Hierarchy(organisation_id=organisation_id, levels=levels)
    previous: list[Location] = []

    for spec in levels:
        type_id = (type_ids or {}).get(spec.name, spec.depth)
        made: list[Location] = []
        for n in range(spec.count):
            # Spread children evenly rather than filling each parent in turn, so no parent ends up
            # with every remainder.
            parent = previous[n % len(previous)] if previous else None
            loc_id = next(ids)
            made.append(Location(
                id=loc_id,
                uuid=f"loc-{organisation_id}-{loc_id}",
                title=f"{spec.name} {n + 1}",
                level_name=spec.name,
                depth=spec.depth,
                parent_id=parent.id if parent else None,
                type_id=type_id,
                organisation_id=organisation_id,
            ))
            h._parent[loc_id] = parent.id if parent else None
        h.locations.extend(made)
        previous = made

    return h
