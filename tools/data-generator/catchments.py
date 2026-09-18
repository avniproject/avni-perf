"""Assign catchments and users, which is what decides how much anyone syncs.

The dataset says what data exists; this says who can see it. Designing them apart produces users
whose catchments do not intersect the data and a simulation that measures nothing (plan G5).

Two facts from plan section E0 shape it:

  * **Field workers in a village share its catchment.** Three ASHAs to a village, and all three pull
    every row recorded there, including the two thirds they did not create. So a field worker's sync
    volume tracks the village's activity rather than their own, and the same rows are read three
    times over -- easy on cache, harder on page contention, and not a shape a
    one-user-per-catchment generator produces.
  * **A supervisor holds a sub-centre**, which expands down the lineage to its ~2.8 villages. One
    catchment, several villages, and every row all those field workers produced.

A catchment is declared against one location and the server expands it to that location's
descendants through `virtual_catchment_address_mapping_table`. So declaring a sub-centre is not the
same as declaring its three villages: the declared rows differ, the expanded set does not, and Q15
counts the expanded one because that is what determines volume.
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

from hierarchy import Hierarchy, Location

FIELD_WORKER = "field_worker"
SUPERVISOR = "supervisor"


@dataclass(frozen=True)
class CatchmentSpec:
    id: int
    uuid: str
    name: str
    organisation_id: int
    # The one location the catchment is declared against. The server expands it downward.
    root: Location
    role: str


@dataclass(frozen=True)
class UserSpec:
    id: int
    uuid: str
    username: str
    organisation_id: int
    catchment_id: int
    role: str
    # D1 branches on this in filterChangedEntities, and G5 requires it to be stable per user.
    device_id: str


def plan(hierarchy: Hierarchy, *, field_workers_per_leaf: int = 3,
         supervisor_level: str = "Sub-Centre", username_prefix: str = "u",
         first_catchment_id: int = 1, first_user_id: int = 1
         ) -> tuple[list[CatchmentSpec], list[UserSpec]]:
    """One catchment per leaf and per supervisor location, and the users that share them."""
    if field_workers_per_leaf < 1:
        raise ValueError("need at least one field worker per leaf location")
    names = {l.name for l in hierarchy.levels}
    if supervisor_level not in names:
        raise ValueError(f"no level named {supervisor_level!r}; have {sorted(names)}")

    cat_ids = itertools.count(first_catchment_id)
    user_ids = itertools.count(first_user_id)
    org = hierarchy.organisation_id
    catchments: list[CatchmentSpec] = []
    users: list[UserSpec] = []

    def add_user(catchment: CatchmentSpec) -> None:
        uid = next(user_ids)
        users.append(UserSpec(
            id=uid,
            uuid=f"user-{org}-{uid}",
            username=f"{username_prefix}{uid}@org{org}",
            organisation_id=org,
            catchment_id=catchment.id,
            role=catchment.role,
            device_id=f"device-{org}-{uid}",
        ))

    for leaf in hierarchy.leaves:
        cid = next(cat_ids)
        c = CatchmentSpec(id=cid, uuid=f"catchment-{org}-{cid}", name=f"{leaf.title} catchment",
                          organisation_id=org, root=leaf, role=FIELD_WORKER)
        catchments.append(c)
        # Every field worker in the village points at the same catchment.
        for _ in range(field_workers_per_leaf):
            add_user(c)

    for loc in hierarchy.at(supervisor_level):
        cid = next(cat_ids)
        c = CatchmentSpec(id=cid, uuid=f"catchment-{org}-{cid}", name=f"{loc.title} catchment",
                          organisation_id=org, root=loc, role=SUPERVISOR)
        catchments.append(c)
        add_user(c)

    return catchments, users


def declared_mappings(catchments: list[CatchmentSpec]) -> list[dict]:
    """`catchment_address_mapping` rows -- the locations an administrator picked, one per catchment.

    The server derives the expanded set itself, so only the declared row is written.
    """
    return [{"catchment_id": c.id, "addresslevel_id": c.root.id} for c in catchments]


def expanded_locations(hierarchy: Hierarchy, catchment: CatchmentSpec) -> list[Location]:
    """What the catchment actually resolves to: its root plus every descendant."""
    return [catchment.root] + hierarchy.descendants(catchment.root)


def catchment_rows(catchments: list[CatchmentSpec], audit_user_id: int = 1) -> list[dict]:
    return [{
        "id": c.id, "uuid": c.uuid, "name": c.name, "organisation_id": c.organisation_id,
        "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id,
    } for c in catchments]


def user_rows(users: list[UserSpec], audit_user_id: int = 1) -> list[dict]:
    return [{
        "id": u.id, "uuid": u.uuid, "username": u.username,
        "organisation_id": u.organisation_id, "catchment_id": u.catchment_id,
        "is_voided": False, "version": 0, "disabled_in_cognito": False,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id,
    } for u in users]


def feeder_rows(users: list[UserSpec]) -> list[dict]:
    """Rows for the simulation's `sync-users.csv`, which needs a stable device id per user (G5)."""
    return [{"userName": u.username, "deviceId": u.device_id, "role": u.role} for u in users]
