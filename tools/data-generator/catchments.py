"""Assign catchments and users, which is what decides how much anyone syncs.

The dataset says what data exists; this says who can see it. Designing them apart produces users
whose catchments do not intersect the data and a simulation that measures nothing (plan G5).

Two facts from the test scenarios shape it:

  * **Field workers in a village share its catchment.** Three ASHAs to a village, and all three pull
    every row recorded there, including the two thirds they did not create. So a field worker's sync
    volume tracks the village's activity rather than their own, and the same rows are read three
    times over -- easy on cache, harder on page contention, and not a shape a
    one-user-per-catchment generator produces.
  * **A supervisor holds a sub-centre**, which expands down the lineage to its ~2.8 villages. One
    catchment, several villages, and every row all those field workers produced.

**A catchment holds many locations.** `catchment_address_mapping` is a many-to-many, and real
configuration uses it -- the bundles examined here carry catchments of three locations each. The
server then expands every declared location down its own subtree through
`virtual_catchment_address_mapping_table`, so the expanded set is the union of those subtrees.

Two consequences. Declaring a sub-centre and declaring its three villages reach the **same villages**
but not quite the same expanded set -- the first also includes the sub-centre location itself -- and
they write a different number of declared rows. For a pilot tenant that is 227 mapping rows against
334. Subjects live at villages, so the difference does not change sync volume, but it does change the
size of the mapping table and what the expansion view has to compute. And Q15 counts the expanded set
rather than the declared one, because that is what determines volume.

**What this generator assumes, and it is an assumption rather than a constraint:** one declared
location per catchment by default -- a village for a field worker, a sub-centre for a supervisor.
`declare_leaves=True` declares the leaves instead, and `plan` accepts any location list directly.
Which shape production uses has not been measured.
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
    # Every location declared against this catchment. The server expands each down its own subtree.
    locations: tuple[Location, ...]
    role: str

    def __post_init__(self) -> None:
        if not self.locations:
            raise ValueError(f"catchment {self.name!r} declares no locations")


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
         first_catchment_id: int = 1, first_user_id: int = 1,
         declare_leaves: bool = False
         ) -> tuple[list[CatchmentSpec], list[UserSpec]]:
    """One catchment per leaf and per supervisor location, and the users that share them.

    `declare_leaves` changes how a supervisor's catchment is written. Declaring the sub-centre
    writes one mapping row and expands to it plus its villages; declaring the villages writes one
    row each and expands to just them. Both reach the same villages, which is what carries subjects.
    """
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
                          organisation_id=org, locations=(leaf,), role=FIELD_WORKER)
        catchments.append(c)
        # Every field worker in the village points at the same catchment.
        for _ in range(field_workers_per_leaf):
            add_user(c)

    for loc in hierarchy.at(supervisor_level):
        cid = next(cat_ids)
        if declare_leaves:
            leaves = tuple(d for d in hierarchy.descendants(loc)
                           if d.level_name == hierarchy.levels[-1].name) or (loc,)
        else:
            leaves = (loc,)
        c = CatchmentSpec(id=cid, uuid=f"catchment-{org}-{cid}", name=f"{loc.title} catchment",
                          organisation_id=org, locations=leaves, role=SUPERVISOR)
        catchments.append(c)
        add_user(c)

    return catchments, users


def declared_mappings(catchments: list[CatchmentSpec]) -> list[dict]:
    """`catchment_address_mapping` rows -- one per declared location, not one per catchment.

    The server derives the expanded set itself, so descendants are never written here.
    """
    return [{"catchment_id": c.id, "addresslevel_id": loc.id}
            for c in catchments for loc in c.locations]


def expanded_locations(hierarchy: Hierarchy, catchment: CatchmentSpec) -> list[Location]:
    """What the catchment resolves to: the union of each declared location and its descendants."""
    seen: dict[int, Location] = {}
    for loc in catchment.locations:
        for l in [loc] + hierarchy.descendants(loc):
            seen[l.id] = l
    return list(seen.values())


# Structural rows -- locations, catchments, users, groups -- are setup, not activity. A fixed
# timestamp well before any dataset's reference date keeps them out of every incremental sync's
# window and makes regeneration byte-identical.
#
# **They cannot be left null.** Every one of these tables carries a BEFORE INSERT trigger that
# copies the row's timestamps into the `audit` table, whose own date columns are NOT NULL with no
# default. A null here fails the insert with a message naming `audit`, not the table being
# written -- which is why it reads as an unrelated problem. `users` is the exception: it has
# CURRENT_TIMESTAMP defaults and no trigger. Supplying them everywhere is both safer and more
# consistent than relying on that.
SETUP_TIMESTAMP = "2020-01-01 00:00:00"


def _stamps() -> dict:
    return {"created_date_time": SETUP_TIMESTAMP, "last_modified_date_time": SETUP_TIMESTAMP}


def catchment_rows(catchments: list[CatchmentSpec], audit_user_id: int = 1) -> list[dict]:
    return [{
        "id": c.id, "uuid": c.uuid, "name": c.name, "organisation_id": c.organisation_id,
        "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **_stamps(),
    } for c in catchments]


def user_rows(users: list[UserSpec], audit_user_id: int = 1) -> list[dict]:
    """The `users` table, which is the one place the audit convention does not hold.

    Three ways it differs from every other table here, all verified against migrations rather
    than assumed, and all of which fail a load rather than degrading it:

    - **No `version`.** `V1_42__DropColumnVersionFromUsers` removed it. Writing it is a column
      that does not exist.
    - **`name` is NOT NULL with no default**, since `V1_328__UserNameIsMandatory`. It is only
      shown in admin screens and no sync query reads it, which is why it was originally left
      out — but "nothing reads it" and "it may be null" are different claims.
    - **`operating_individual_scope` is NOT NULL with no default.** `ByCatchment` rather than
      `None`, because that is what `UserAndCatchmentWriter` sets for a user who has a catchment,
      and `None` would leave the sync unscoped.
    """
    return [{
        "id": u.id, "uuid": u.uuid, "username": u.username, "name": u.username,
        "organisation_id": u.organisation_id, "catchment_id": u.catchment_id,
        "operating_individual_scope": "ByCatchment",
        "is_voided": False, "disabled_in_cognito": False,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **_stamps(),
    } for u in users]


# One group per organisation, carrying every privilege. Ids are derived from the organisation so
# they are stable across regenerations and cannot collide between tenants.
GROUP_ID_STRIDE = 1_000_000


def group_id_for(organisation_id: int) -> int:
    return GROUP_ID_STRIDE + organisation_id


def group_rows(organisation_ids, audit_user_id: int = 1) -> list[dict]:
    """The group every generated user belongs to (G5).

    **Without this a generated user syncs almost nothing, and does so silently.**
    `SyncDetailsService.getAllSyncableItems` gates each subject type on
    `hasPrivilege(ViewSubject, ...)`, encounters on `ViewVisit` and enrolments on
    `ViewEnrolmentDetails`. Privileges resolve from `user_group` -> `groups`: either the group has
    `has_all_privileges`, or explicit `group_privilege` rows are matched. A user in no group gets
    neither, so **19 of the 75 pulled entities disappear** -- every one that carries field data,
    including `individual`, `encounter`, `program_encounter` and `program_enrolment`.

    The run still completes. It just measures reference data against a dataset it never reads,
    which is the kind of green result this whole exercise exists not to produce.

    **`has_all_privileges` rather than explicit rows, deliberately.** A real deployment may grant a
    field worker a narrower set, and that would change which entities sync. All-privileges is the
    heavier and less surprising choice: every entity the dataset contains is pulled, so the load is
    what the scenarios specify rather than a subset nobody chose. Narrow it only with a measurement
    saying production is narrower.
    """
    return [{
        "id": group_id_for(org), "uuid": f"group-{org}", "name": "Everyone",
        "has_all_privileges": True, "organisation_id": org,
        "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **_stamps(),
    } for org in sorted(set(organisation_ids))]


def user_group_rows(users: list[UserSpec], audit_user_id: int = 1) -> list[dict]:
    """Membership linking each generated user to its organisation's group (G5).

    `version` is not decoration here: `CHSEntity.version` is a primitive `int`, so a NULL in this
    column makes the row unreadable by Hibernate and every `syncDetails` call 500s. That is not
    hypothetical -- it is the first failure the first live run produced, from a hand-provisioned
    user whose `user_group` row had a null version.
    """
    return [{
        "id": u.id, "uuid": f"usergroup-{u.organisation_id}-{u.id}",
        "user_id": u.id, "group_id": group_id_for(u.organisation_id),
        "organisation_id": u.organisation_id,
        "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **_stamps(),
    } for u in users]


def feeder_rows(users: list[UserSpec]) -> list[dict]:
    """Rows for the simulation's `sync-users.csv`, which needs a stable device id per user (G5)."""
    return [{"userName": u.username, "deviceId": u.device_id, "role": u.role} for u in users]
