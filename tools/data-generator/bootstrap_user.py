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
    # **Scoped to the organisation as well as the uuid.** Every uuid this file mints carries the
    # organisation already, so today the uuid alone is unambiguous -- but the guarantee lives in
    # the values rather than in the query, and `address_level_type` is precisely where it would
    # not hold: a bundle's uuids are reused in every organisation it is imported into, so the
    # bundle's Village exists three times over with three different ids. Point this helper at a
    # bundle uuid without the scope and it adopts whichever tenant's row came back first.
    scope = ""
    if "organisation_id" in row and not isinstance(row["organisation_id"], Raw):
        scope = f" and organisation_id = {quote(row['organisation_id'])}"
    return [
        f"    select id into {var} from {table} where uuid = {quote(uuid)}{scope};",
        f"    if {var} is null then",
        f"      insert into {table} ({cols}) values ({vals}) returning id into {var};",
        f"    end if;",
    ]


def cohort_usernames(username: str, count: int) -> list[str]:
    """`cohort@org3` and 3 gives `cohort1@org3`, `cohort2@org3`, `cohort3@org3`.

    The index goes before the `@` because the part after it is how the server finds the
    organisation. A suffix on the whole string would produce users belonging nowhere.
    """
    if count < 1:
        raise ValueError("count starts at 1")
    if count == 1:
        return [username]
    local, at, domain = username.partition("@")
    return [f"{local}{i}{at}{domain}" for i in range(1, count + 1)]


def statements(organisation_id: int, username: str, audit_user_id: int = 1,
               count: int = 1) -> list[str]:
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
    # **Identity is per user, and it was per organisation.** `upsert` finds a row by its uuid, so
    # one uuid for the whole organisation meant a second invocation with a different username
    # found the first user and did nothing -- reporting success and creating nobody. Fine while
    # this only ever made one user for environment-check.sh; wrong the moment case 1 wanted a
    # hundred. The `bootstrap-user-` prefix stays, because `teardown_org.py` cuts generated users
    # on `user-<org>-%` and these are deliberately outside that: a teardown should not remove the
    # user the next environment check runs as.
    usernames = cohort_usernames(username, count)
    users = [cat.UserSpec(id=0, uuid=f"bootstrap-user-{org}-{u}", username=u,
                          organisation_id=org, catchment_id=0, role=cat.FIELD_WORKER,
                          device_id=f"bootstrap-device-{org}-{u}")
             for u in usernames]

    def without_id(row: dict, **overrides) -> dict:
        out = {k: v for k, v in row.items() if k != "id"}
        out.update(overrides)
        return out

    out = [
        f"-- {len(usernames)} syncable user(s). No dataset, no bundle, no metadata.",
        f"-- Organisation {org}, user(s) {usernames[0]}"
        + (f" .. {usernames[-1]}" if len(usernames) > 1 else "") + ".",
        "-- They share one location, one catchment and one group: a training cohort in one",
        "-- village, which is what case 1 models. Only the user and its membership are per user.",
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
    # **The type has to be one the organisation permits registration at.**
    #
    # This invented its own -- `bootstrap-type-3`, name "Village", nothing to do with the bundle's
    # Village. Where an organisation sets `customRegistrationLocations`, that is the exact failure
    # found on 30 Sep 2026: the rule names the bundle's Village uuid, the catchment resolves to a
    # location of a type that is not on the list, and
    # `getAddressLevelsForCatchmentAndMatchingAddressLevelTypeIds` returns empty. The server then
    # drops every entity keyed by `subjectTypeUuid` -- Individual, ProgramEnrolment,
    # ProgramEncounter, the subject approval statuses -- from `syncDetails`. `Encounter` is keyed
    # on encounter type and never applies the filter, so the user still syncs *something* and the
    # run looks fine.
    #
    # So resolve a permitted type first and only invent one where the organisation has no rule.
    # Deepest permitted type, by level ascending: a village rather than a state, which is what a
    # field worker's catchment looks like.
    out += [
        "    -- A type this organisation permits subject registration at, if it restricts them.",
        "    select alt.id into v_type_id",
        "      from organisation_config oc",
        "      cross join lateral jsonb_array_elements(",
        "             oc.settings::jsonb -> 'customRegistrationLocations') e",
        "      cross join lateral jsonb_array_elements_text(e -> 'locationTypeUUIDs') u",
        "      join address_level_type alt",
        "        on alt.uuid = u and alt.organisation_id = oc.organisation_id",
        "       and alt.is_voided = false",
        f"     where oc.organisation_id = {org}",
        "       and oc.settings::jsonb ? 'customRegistrationLocations'",
        "       and jsonb_typeof(oc.settings::jsonb -> 'customRegistrationLocations') = 'array'",
        "     order by alt.level",
        "     limit 1;",
        "",
        "    if v_type_id is null then",
        "      -- No permitted type resolved. If the organisation has a rule at all, inventing a",
        "      -- type here would hand back a user whose Individual never syncs, which is worse",
        "      -- than no user: the run completes and the result is wrong rather than absent.",
        "      if exists (select 1 from organisation_config oc",
        f"                  where oc.organisation_id = {org}",
        "                    and oc.settings::jsonb ? 'customRegistrationLocations'",
        "                    and jsonb_typeof(",
        "                          oc.settings::jsonb -> 'customRegistrationLocations') = 'array'",
        "                    and jsonb_array_length(",
        "                          oc.settings::jsonb -> 'customRegistrationLocations') > 0) then",
        f"        raise exception 'organisation {org} restricts registration to location types "
        "that do not resolve to any address_level_type it owns. A bootstrap user built on an "
        "invented type would be dropped from syncDetails for every subject-typed entity. Fix the "
        "rule or the types before bootstrapping.';",
        "      end if;",
        "    end if;",
        "",
        "    if v_type_id is null then",
    ]
    out += ["  " + line for line in upsert("address_level_type", {
        "uuid": village.uuid.replace("location", "type"), "name": "Village", "level": 1.0,
        "organisation_id": org, "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id, **cat._stamps(),
    }, "v_type_id")]
    out += ["    end if;"]

    # `address_level` has no `level` column -- that is on `address_level_type`, where it is
    # nullable. Here depth is carried by `lineage` and `type_id`, and the name column is `title`.
    #
    # **`lineage` has to be right in the INSERT itself**, so the id is taken from the sequence
    # first rather than corrected afterwards.
    #
    # `address_level` carries a CHECK that a root row's lineage equals its own id:
    #
    #     (parent_id IS NULL AND lineage ~ (''||id)::lquery)
    #
    # This wrote `lineage = '0'` and fixed it on the next statement, which a CHECK never allows --
    # it is evaluated on the insert, not at commit, and CHECK constraints cannot be DEFERRABLE in
    # PostgreSQL. So the whole transaction rolled back and nothing was written. `nextval` on the
    # column's own sequence gives the id before the row exists, which is one extra statement and
    # no constraint to fight.
    #
    # The second rollback was the cast: `lineage` is `ltree`, and there is no implicit or
    # assignment cast from text, so `v_loc_id::text` is rejected and it needs `::text::ltree`.
    # Both failures were in the same INSERT, and the first hid the second.
    loc_row = {
        "id": Raw("v_loc_id"), "uuid": village.uuid, "title": village.title,
        # `::text::ltree`, not `::text`. The column is `ltree` -- which the CHECK gives away, since
        # `nlevel()` and `subltree()` only take one -- and PostgreSQL has no implicit or assignment
        # cast from text to it, so an int cast to text is rejected on the way in.
        "lineage": Raw("v_loc_id::text::ltree"), "type_id": Raw("v_type_id"),
        "organisation_id": org,
        "is_voided": False, "version": 0, "created_by_id": audit_user_id,
        "last_modified_by_id": audit_user_id, **cat._stamps(),
    }
    out += [
        f"    select id into v_loc_id from address_level where uuid = {quote(village.uuid)}"
        f" and organisation_id = {org};",
        "    if v_loc_id is null then",
        "      v_loc_id := nextval(pg_get_serial_sequence('address_level', 'id'));",
        f"      insert into address_level ({', '.join(loc_row)})",
        f"      values ({', '.join(quote(v) for v in loc_row.values())});",
        "    end if;",
    ]
    # **Re-point an existing bootstrap location at the permitted type.** The upsert above finds
    # it by uuid, so an organisation where the earlier version of this script already ran keeps
    # the invented type it was created with -- and keeps the syncDetails failure with it. Without
    # this the fix would only reach organisations nobody had bootstrapped yet, which are the ones
    # that did not have the problem.
    out.append("    update address_level set type_id = v_type_id "
               "where id = v_loc_id and type_id is distinct from v_type_id;")

    for row in cat.catchment_rows([catchment], audit_user_id):
        out += upsert("catchment", without_id(row), "v_catchment_id")
    for row in cat.group_rows({org: 0}, audit_user_id):
        out += upsert("groups", without_id(row), "v_group_id")
    for u in users:
        for row in cat.user_rows([u], audit_user_id):
            out += upsert("users", without_id(row, catchment_id=Raw("v_catchment_id")),
                          "v_user_id")
        for row in cat.user_group_rows([u], audit_user_id, group_ids={org: 0}):
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
        "    raise notice 'organisation %: % user(s), last id %, catchment %, location %',",
        f"      {org}, {len(usernames)}, v_user_id, v_catchment_id, v_loc_id;",
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
    ap.add_argument("--count", type=int, default=1,
                    help="how many users; the index goes before the @ (default 1)")
    a = ap.parse_args()
    print("\n".join(statements(a.organisation, a.username, a.audit_user, a.count)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
