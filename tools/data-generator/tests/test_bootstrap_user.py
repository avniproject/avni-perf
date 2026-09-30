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


# Who must exist before whom. Asserted as dependencies rather than as one fixed sequence, so
# reordering the independent rows does not fail a test that is really about foreign keys.
DEPENDS_ON = {
    "address_level": ["address_level_type"],
    "catchment_address_mapping": ["catchment", "address_level"],
    "users": ["catchment"],
    "user_group": ["users", "groups"],
}


def test_every_row_is_created_after_the_rows_it_points_at():
    s = sql()
    for table, parents in DEPENDS_ON.items():
        child = s.index(f"insert into {table} ")
        for parent in parents:
            assert s.index(f"insert into {parent} ") < child, (
                f"{table} is inserted before {parent}, which fails on the spot")


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
    for raw in sql().splitlines():
        # Indented: the inserts live inside a DO block now. Matching on the unindented form made
        # this loop body unreachable and the test passed by doing nothing.
        line = raw.strip()
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
    users = [l.strip() for l in sql().splitlines()
             if l.strip().startswith("insert into users ")][0]
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


def test_the_ceiling_sits_above_everything_the_generator_writes():
    """It bounds teardown_org.py's range cut from above.

    A cut of `id >= id_base and id < ceiling` is what separates rows the generator wrote from rows
    the server assigned. If the pilot deployment's ids reached past the ceiling, a teardown would
    leave the top of a dataset behind and the next load would fail on the primary key.
    """
    import recipe as recipe_mod
    import deployment as dep
    from pathlib import Path as P
    pilot = P(__file__).resolve().parents[1] / "datasets" / "pilot-day-180.json"
    d = recipe_mod.Recipe.load(pilot).to_deployment()
    top = max(dep.plan_ids(d).values()) + dep.ID_STRIDE
    assert boot.GENERATED_ID_CEILING > top, (
        f"bootstrap starts at {boot.GENERATED_ID_CEILING:,}, pilot ids reach {top:,}")


def test_the_username_reaches_the_users_row_and_is_escaped():
    assert "'o''brien@org'" in sql(username="o'brien@org"), "a quote must not break the SQL"


def test_the_audit_user_is_configurable():
    """created_by_id points at a user that must already exist; it is not always 1.

    Checked by column rather than by position: the first version asserted on ", 42, 42)" at the
    end of the values list, which broke the moment timestamps were appended after it.
    """
    import catchments as cat
    import hierarchy as hy
    catchments, _ = cat.plan(hy.build(1, 2))
    row = cat.catchment_rows(catchments, 42)[0]
    assert row["created_by_id"] == 42 and row["last_modified_by_id"] == 42
    assert "42" in sql(audit_user_id=42)


def test_every_row_carries_the_timestamps_its_trigger_needs():
    """Every table here but `users` has a BEFORE INSERT trigger copying the row's timestamps into
    `audit`, whose date columns are NOT NULL with no default. A null fails the insert with a
    message naming `audit` rather than the table being written."""
    for line in sql().splitlines():
        if line.startswith("insert into") and "catchment_address_mapping" not in line:
            assert "created_date_time" in line, line
            assert "last_modified_date_time" in line, line


# --- the fix: ids come from the sequence -------------------------------------------------------
#
# Every row used to be written at a fixed id, the same value whatever organisation was asked for.
# With `insert ... on conflict do nothing`, a second organisation's bootstrap hit the first
# organisation's rows, did nothing, and reported success -- leaving environment-check.sh to fail
# with "no such user" against an environment that was fine.

def test_nothing_is_written_at_a_fixed_id():
    """Allocating per organisation would not have fixed it either: on the load environment the
    server's own address_level_type ids run from 2,100,000,001 upward, immediately above the row a
    bootstrap wrote at 2,100,000,000, so a per-organisation band would land inside territory the
    server is handing out. Letting the sequence assign removes the question."""
    s = sql(organisation=10)
    assert str(boot.GENERATED_ID_CEILING) not in s
    assert "returning id into" in s


def test_two_organisations_share_no_identifier():
    """The collision that was silent. Every uuid carries the organisation, so nothing is shared."""
    import re
    a, b = sql(organisation=1), sql(organisation=10)
    quoted = lambda t: set(re.findall(r"'(bootstrap-[a-z]+-\d+|group-\d+|usergroup-\d+-\d+)'", t))
    assert quoted(a) and quoted(a).isdisjoint(quoted(b))


def test_each_row_is_found_by_the_uuid_it_inserts():
    """The guard and the insert have to name the same uuid or the guard never matches and a re-run
    fails on the unique constraint instead of doing nothing. The first version of this rewrite
    looked for `usergroup-bootstrap-1` while inserting `usergroup-1-0`."""
    import re
    s = sql()
    guards = re.findall(r"select id into (\w+) from (\w+) where uuid = '([^']+)'", s)
    assert len(guards) >= 5
    for var, table, uuid in guards:
        insert = re.search(rf"insert into {table} \(([^)]*)\) values \(([^)]*)\)", s)
        assert insert, table
        assert f"'{uuid}'" in insert.group(2), f"{table} guards on {uuid} but inserts something else"


def test_a_foreign_key_refers_to_the_value_just_assigned():
    """Not to a constant. `users.catchment_id` is the catchment this run created, whatever id the
    sequence gave it."""
    s = sql()
    users = [l.strip() for l in s.splitlines() if l.strip().startswith("insert into users ")][0]
    assert "v_catchment_id" in users
    ug = [l.strip() for l in s.splitlines() if l.strip().startswith("insert into user_group ")][0]
    assert "v_user_id" in ug and "v_group_id" in ug


def test_it_is_one_transaction_and_says_what_it_made():
    s = sql()
    assert s.index("begin;") < s.index("do $$") < s.rindex("commit;")
    assert "raise notice" in s, "a run that creates nothing should still say so"
