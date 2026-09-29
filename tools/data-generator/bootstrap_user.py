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

# Above anything a generated dataset can reach, so a bootstrap user can coexist with one if
# someone loads a dataset without restoring first.
#
# The first attempt at this was two billion, which is *below* the range in use: `plan_ids` gives
# each tenant `i * ID_STRIDE`, and the committed co-tenant deployment has 513 tenants, so ids
# already reach 51.3 billion. A test caught it. Nine trillion leaves three orders of magnitude of
# headroom and is still comfortably inside a bigint.
BOOTSTRAP_ID_BASE = 9_000_000_000_000


def quote(v) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def insert(table: str, row: dict) -> str:
    # `on conflict do nothing` without a target, because not every table here has an `id`:
    # `catchment_address_mapping` is a bare join table, and naming a column it does not have
    # turns a re-run into a syntax error rather than a no-op.
    cols = ", ".join(row)
    vals = ", ".join(quote(v) for v in row.values())
    return f"insert into {table} ({cols}) values ({vals}) on conflict do nothing;"


def statements(organisation_id: int, username: str, audit_user_id: int = 1) -> list[str]:
    base = BOOTSTRAP_ID_BASE
    # **One location, not a hierarchy.** The generator's six-level tree is the right shape for a
    # dataset and the wrong shape here: every level needs an `address_level_type` row to point at,
    # and those come from `refs.json`, which is dumped from the database this is meant to run
    # before. A catchment needs somewhere to point and nothing more, so this emits one type and
    # one location and owns both.
    village = hy.Location(id=base, uuid=f"bootstrap-location-{organisation_id}",
                          title="Bootstrap Village", level_name="Village", depth=1,
                          parent_id=None, type_id=base, organisation_id=organisation_id)

    catchment = cat.CatchmentSpec(id=base + 1, uuid=f"bootstrap-catchment-{organisation_id}",
                                  name="Bootstrap catchment", organisation_id=organisation_id,
                                  locations=(village,), role=cat.FIELD_WORKER)
    user = cat.UserSpec(id=base + 1, uuid=f"bootstrap-user-{organisation_id}", username=username,
                        organisation_id=organisation_id, catchment_id=catchment.id,
                        role=cat.FIELD_WORKER, device_id=f"bootstrap-device-{organisation_id}")

    out = [
        "-- One syncable user for environment-check.sh. No dataset, no bundle, no metadata.",
        f"-- Organisation {organisation_id}, user {username}. Re-runnable.",
        "begin;",
    ]
    out.append(insert("address_level_type", {
        "id": village.type_id, "uuid": f"bootstrap-type-{organisation_id}", "name": "Village",
        "level": 1.0, "organisation_id": organisation_id, "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id,
    }))
    out.append(insert("address_level", {
        "id": village.id, "uuid": village.uuid, "title": village.title, "level": 1.0,
        "type_id": village.type_id, "organisation_id": organisation_id,
        "is_voided": False, "version": 0,
        "created_by_id": audit_user_id, "last_modified_by_id": audit_user_id,
    }))
    for row in cat.catchment_rows([catchment], audit_user_id):
        out.append(insert("catchment", row))
    for row in cat.declared_mappings([catchment]):
        out.append(insert("catchment_address_mapping", row))
    for row in cat.group_rows([organisation_id], audit_user_id):
        out.append(insert("groups", row))
    for row in cat.user_rows([user], audit_user_id):
        out.append(insert("users", row))
    for row in cat.user_group_rows([user], audit_user_id):
        out.append(insert("user_group", row))
    out.append("commit;")
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
