import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap_user as boot
import catchments as cat


def sql(**kw):
    return "\n".join(boot.statements(kw.pop("organisation", 1),
                                     kw.pop("username", "loadtest@openchs"), **kw))


def test_it_needs_nothing_the_environment_cannot_already_provide():
    """The whole point: no bundle, no columns.json, no refs.json, no dataset.

    Those are what make the generator's normal path depend on a loaded database, which is the
    thing this check is supposed to run before.
    """
    s = sql()
    # It owns its own address_level_type rather than looking one up from refs.json.
    assert "insert into address_level_type" in s
    assert s.index("address_level_type") < s.index("insert into address_level ")


def test_every_table_the_user_depends_on_is_created_in_order():
    s = sql()
    order = [s.index(f"insert into {t} ") for t in
             ("address_level_type", "address_level", "catchment",
              "catchment_address_mapping", "groups", "users", "user_group")]
    assert order == sorted(order), "a child row inserted before its parent fails on the spot"


def test_the_user_can_actually_resolve_privileges():
    """A user without group membership syncs none of the entities carrying field data, and the
    run still reports success. That is the defect this bootstrap exists not to reproduce."""
    s = sql()
    assert "insert into groups" in s and "has_all_privileges" in s
    assert "insert into user_group" in s


def test_it_is_re_runnable():
    for line in sql().splitlines():
        if line.startswith("insert into"):
            assert line.rstrip().endswith("on conflict do nothing;"), line
            # Naming a conflict target breaks on catchment_address_mapping, which has no id.
            assert "on conflict (" not in line, line


# The two tables that do not carry `version`, and the migration that took it away from each.
# Named rather than skipped, so adding a third is a deliberate act.
NO_VERSION = {"catchment_address_mapping": "V0_38", "users": "V1_42"}


def test_every_row_carries_a_version_except_the_two_that_cannot():
    """version is a primitive int on CHSEntity: NULL makes the row unreadable and syncDetails
    500s. That is the first failure the first live run produced.

    But writing it where the column was dropped fails the insert outright, which is how the live
    schema caught this. Both directions are wrong, so the exceptions are enumerated.
    """
    for line in sql().splitlines():
        if not line.startswith("insert into"):
            continue
        table = line.split()[2]
        if table in NO_VERSION:
            assert "version" not in line, f"{table} lost version in {NO_VERSION[table]}: {line}"
        else:
            assert "version" in line, line
        if table != "catchment_address_mapping":
            assert "created_by_id" in line and "last_modified_by_id" in line, line


def test_the_users_row_carries_what_the_live_schema_makes_mandatory():
    """Both are NOT NULL with no default, and both were originally left out on the grounds that
    nothing on the sync path reads them. "Nothing reads it" and "it may be null" are different
    claims, and the second is the one that decides whether the insert succeeds."""
    users = [l for l in sql().splitlines() if l.startswith("insert into users ")][0]
    assert " name," in users, "users.name is NOT NULL since V1_328"
    assert "operating_individual_scope" in users, "NOT NULL, and None would leave sync unscoped"
    assert "'ByCatchment'" in users, "what UserAndCatchmentWriter sets for a catchment user"


def test_every_id_fits_in_int4():
    """The id columns are SERIAL, which is int4, not bigint.

    `V0_1__CreateTables` declares `id SERIAL PRIMARY KEY` and nothing since widens it, so an id
    above 2,147,483,647 fails the insert outright with "integer out of range". An earlier base of
    nine trillion was chosen to clear the generated range and cleared int4 as well.
    """
    import re
    for line in sql().splitlines():
        for n in (int(m) for m in re.findall(r"\b(\d{8,})\b", line)):
            assert n <= boot.INT4_MAX, f"{n:,} exceeds int4 in: {line[:90]}"


def test_bootstrap_ids_sit_above_the_pilot_deployment():
    """A bootstrap user may sit beside a dataset if someone loads one without restoring first."""
    import recipe as recipe_mod
    import deployment as dep
    from pathlib import Path as P
    pilot = P(__file__).resolve().parents[1] / "datasets" / "pilot-day-180.json"
    d = recipe_mod.Recipe.load(pilot).to_deployment()
    top = max(dep.plan_ids(d).values()) + dep.ID_STRIDE
    assert boot.BOOTSTRAP_ID_BASE > top, (
        f"bootstrap starts at {boot.BOOTSTRAP_ID_BASE:,}, pilot ids reach {top:,}")


def test_the_username_reaches_the_users_row_and_is_escaped():
    assert "'o''brien@org'" in sql(username="o'brien@org"), "a quote must not break the SQL"


def test_the_audit_user_is_configurable():
    """created_by_id points at a user that must already exist; it is not always 1."""
    assert ", 42, 42)" in sql(audit_user_id=42)
