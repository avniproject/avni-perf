"""One syncable user, as SQL, with no dataset behind it.

**Why this exists.** `environment-check.sh` needs a username to ask the questions that matter —
does auth work, does `syncDetails` answer, does the user resolve privileges. But the users the
scenarios run as come from the dataset generator, which needs a bundle, a `columns.json` and a
`refs.json` dumped from the target database, and a multi-hour load. So the check that is supposed
to de-risk the expensive thing could only run after it. That is the wrong way round.

**It sidesteps all three dependencies.** A user needs no metadata: no subject types, no form
mappings, no concepts. Only an organisation that already exists, one location, a catchment
declaring it, a group carrying privileges, and the membership row joining them. That is plain SQL
with explicit columns, so no `columns.json`; no observations, so no bundle; no metadata ids, so no
`refs.json`.

**The rows come from the generator's own builders**, so a bootstrap user is shaped exactly like a
generated one. If `version` or the audit columns are ever wrong here they are wrong there too,
which is the failure the first live run produced.

    python3 bootstrap_user.py --organisation 1 --username loadtest@openchs > user.sql

Re-runnable: every insert is `ON CONFLICT DO NOTHING`.
"""
from __future__ import annotations

import argparse
import sys

import catchments as cat
import hierarchy as hy

# **The ceiling of the generated range, and nothing is written at it.**
#
# It was `BOOTSTRAP_ID_BASE`: the id this file wrote its rows at. That was wrong twice over -- the
# same value for every organisation, so a second bootstrap collided and `on conflict do nothing`
# swallowed it; and the band is not free, because the server's own sequences now allocate from
# just above it. Ids here come from the sequence instead, so this constant no longer names a
# place anything is written.
#
# What it still does is bound `teardown_org.py`'s range cut from above: generated rows sit between
# a dataset's `id_base` and this, so a cut of `id >= id_base and id < this` removes what the
# generator wrote and leaves what the server assigned. Kept here because that is a fact about the
# generator's id space, which this module already reasons about.
#
# **These id columns are `SERIAL`, which is int4.** Not bigint -- `V0_1__CreateTables` declares
# `id SERIAL PRIMARY KEY` and nothing since widens it, so every id has to fit under 2,147,483,647.
# An earlier base of nine trillion cleared the generated range and cleared int4 as well.
INT4_MAX = 2_147_483_647
GENERATED_ID_CEILING = 2_100_000_000


class Raw(str):
    """A SQL expression emitted as written, for referring to a value the database just assigned."""


def quote(v) -> str:
    if isinstance(v, Raw):
        return str(v)
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert(table: str, row: dict) -> str:
    """A bare insert, for a table with nothing to look itself up by."""
    cols = ", ".join(row)
    vals = ", ".join(quote(v) for v in row.values())
    return f"    insert into {table} ({cols}) values ({vals});"


def upsert(table: str, row: dict, var: str, uuid: str | None = None) -> list[str]:
    """Find this row by uuid or create it, leaving its id in `var`.

    **The id comes from the sequence, not from a constant.** Every row here used to be written at a
    fixed `GENERATED_ID_CEILING`, the same value whatever organisation was asked for, and `insert ...
    on conflict do nothing` turned the second organisation's collision into a silent no-op: the
    script reported success, created no user, and `environment-check.sh` then failed with "no such
    user" -- sending you to debug an environment that was fine.

    Allocating per organisation would not have fixed it either, because the band is no longer free.
    On the load environment the server's own `address_level_type` ids now run from 2,100,000,001
    upward, immediately above the row a bootstrap wrote at 2,100,000,000, so a per-organisation
    band would land inside territory the server is handing out.

    Letting the sequence assign removes the question. The uuid is what makes it re-runnable, and it
    already carries the organisation, so two organisations cannot collide however many times this
    runs.
    """
    # Guarded on the row's own uuid by default. Passing a different one is how the two get out
    # of step: the first version looked for `usergroup-bootstrap-1` while inserting
    # `usergroup-1-0`, so the guard never matched and a re-run failed on the unique uuid instead
    # of doing nothing.
    uuid = row["uuid"] if uuid is None else uuid
    assert uuid == row["uuid"], f"{table}: guarded on {uuid!r} but inserting {row['uuid']!r}"
    cols = ", ".join(row)
    vals = ", ".join(quote(v) for v in row.values())
    return [
        f"    select id into {var} from {table} where uuid = {quote(uuid)};",
        f"    if {var} is null then",
        f"      insert into {table} ({cols}) values ({vals}) returning id into {var};",
        f"    end if;",
    ]


def statements(organisation_id: int, username: str, audit_user_id: int = 1) -> list[str]:
    org = organisation_id
    # **One location, not a hierarchy.** The generator's six-level tree is the right shape for a
    # dataset and the wrong shape here: every level needs an `address_level_type` row to point at,
    # and those come from `refs.json`, which is dumped from the database this is meant to run
    # before. A catchment needs somewhere to point and nothing more, so this emits one type and
    # one location and owns both.
    #
    # Ids are the database's to assign; the uuids below are what identify these rows, and each
    # already carries the organisation. See `upsert` for why that changed.
    village = hy.Location(id=0, uuid=f"bootstrap-location-{org}", title="Bootstrap Village",
                          level_name="Village", depth=1, parent_id=None, type_id=0,
                          organisation_id=org)
    catchment = cat.CatchmentSpec(id=0, uuid=f"bootstrap-catchment-{org}",
                                  name="Bootstrap catchment", organisation_id=org,
                                  locations=(village,), role=cat.FIELD_WORKER)
    user = cat.UserSpec(id=0, uuid=f"bootstrap-user-{org}", username=username,
                        organisation_id=org, catchment_id=0, role=cat.FIELD_WORKER,
                        device_id=f"bootstrap-device-{org}")

    def without_id(row: dict, **overrides) -> dict:
        out = {k: v for k, v in row.items() if k != "id"}
        out.update(overrides)
        return out

    out = [
        "-- One syncable user for environment-check.sh. No dataset, no bundle, no metadata.",
        f"-- Organisation {org}, user {username}.",
        "--",
        "-- Re-runnable, and safe to run for several organisations: every row is found by a uuid",
        "-- that carries the organisation, and created only when absent. Ids come from the",
        "-- sequence, so nothing here can collide with what the server allocates.",
        "begin;",
        "do $$",
        "declare",
        "  v_type_id int; v_loc_id int; v_catchment_id int; v_group_id int;",
        "  v_user_id int; v_user_group_id int;",
        "begin",
    ]
    out += upsert("address_level_type", {
        "uuid": village.uuid.replace("location", "type"), "name": "Village", "level": 1.0,
        "organisation_id": org, "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **cat._stamps(),
    }, "v_type_id")

    # `address_level` has no `level` column -- that is on `address_level_type`, where it is
    # nullable. Here depth is carried by `lineage` and `type_id`, and the name column is `title`.
    #
    # `lineage` is the row's own id for a root location, which is only known once the sequence has
    # assigned it, so it is written in a second step rather than guessed.
    out += upsert("address_level", {
        "uuid": village.uuid, "title": village.title, "lineage": "0",
        "type_id": Raw("v_type_id"), "organisation_id": org, "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **cat._stamps(),
    }, "v_loc_id")
    out.append("    update address_level set lineage = v_loc_id::text "
               "where id = v_loc_id and lineage <> v_loc_id::text;")

    for row in cat.catchment_rows([catchment], audit_user_id):
        out += upsert("catchment", without_id(row), "v_catchment_id")
    for row in cat.group_rows({org: 0}, audit_user_id):
        out += upsert("groups", without_id(row), "v_group_id")
    for row in cat.user_rows([user], audit_user_id):
        out += upsert("users", without_id(row, catchment_id=Raw("v_catchment_id")),
                      "v_user_id")
    for row in cat.user_group_rows([user], audit_user_id, group_ids={org: 0}):
        out += upsert("user_group", without_id(row, user_id=Raw("v_user_id"),
                                               group_id=Raw("v_group_id")),
                      "v_user_group_id")

    # `catchment_address_mapping` has no uuid to be found by, so it is guarded on the pair it
    # carries. Both sides are ids the sequence has just assigned.
    out += [
        "    if not exists (select 1 from catchment_address_mapping",
        "                    where catchment_id = v_catchment_id and addresslevel_id = v_loc_id) then",
        "      insert into catchment_address_mapping (catchment_id, addresslevel_id)",
        "      values (v_catchment_id, v_loc_id);",
        "    end if;",
        "",
        "    raise notice 'organisation %: user % (id %), catchment %, location %',",
        f"      {org}, {quote(username)}, v_user_id, v_catchment_id, v_loc_id;",
        "end $$;",
        "commit;",
    ]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--organisation", type=int, required=True,
                    help="an organisation that already exists in the target")
    ap.add_argument("--username", required=True, help="e.g. loadtest@openchs")
    ap.add_argument("--audit-user", type=int, default=1,
                    help="an existing user id for created_by/last_modified_by; usually the admin")
    a = ap.parse_args()
    print("\n".join(statements(a.organisation, a.username, a.audit_user)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
