import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import re

import bootstrap_user as boot
bu = boot
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
        # `re.S` and `\s*`: address_level's insert spans two lines, because its id comes from
        # the sequence before the row exists and the column list no longer fits on one.
        insert = re.search(rf"insert into {table} \(([^)]*)\)\s*values \(([^)]*)\)", s, re.S)
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


def test_a_cohort_gives_every_user_its_own_identity():
    """**The defect this replaces reported success and created nobody.** `upsert` finds a row by
    its uuid, and the uuid was `bootstrap-user-<org>` -- one per organisation. A second call with
    a different username found the first user and did nothing. Fine while this made one user for
    environment-check.sh; wrong the moment case 1 wanted a hundred."""
    sql = "\n".join(bu.statements(3, "cohort@org3", count=5))
    uuids = set(re.findall(r"bootstrap-user-3-[A-Za-z0-9@.]+", sql))
    assert len(uuids) == 5, f"expected five distinct user uuids, got {sorted(uuids)}"
    # Not deviceId: `users` has no such column -- it lives in the feeder, not the database.
    # The uuid and the username are what identify a user here.
    names = set(re.findall(r"'(cohort\d+@org3)'", sql))
    assert len(names) == 5, f"expected five distinct usernames, got {sorted(names)}"


def test_a_cohort_shares_one_catchment_location_and_group():
    """A training cohort is a hundred new workers in one village, which is what case 1 models.
    Only the user and its membership are per user; a catchment each would be a different case."""
    sql = "\n".join(bu.statements(3, "cohort@org3", count=5))
    assert sql.count("bootstrap-catchment-3") == 2, "one catchment, found once and inserted once"
    assert sql.count("bootstrap-location-3") == 2


def test_the_index_goes_before_the_at_sign():
    """The part after `@` is how the server finds the organisation. A suffix on the whole string
    would produce users belonging nowhere."""
    assert bu.cohort_usernames("cohort@org3", 3) == [
        "cohort1@org3", "cohort2@org3", "cohort3@org3"]
    assert bu.cohort_usernames("solo@org3", 1) == ["solo@org3"], "one user keeps its exact name"


def test_bootstrap_users_survive_a_teardown():
    """`teardown_org.py` cuts generated users on `user-<org>-%`. These are deliberately outside
    it: a teardown should not remove the user the next environment check runs as."""
    import teardown_org as td
    sql = "\n".join(bu.statements(3, "cohort@org3", count=3))
    for uuid in re.findall(r"'(bootstrap-user-3-[^']+)'", sql):
        assert not uuid.startswith("user-3-"), uuid


def test_the_registration_type_is_resolved_before_one_is_invented():
    """**The 30 Sep failure, in the one tool that could reintroduce it.**

    This invented an `address_level_type` of its own. Where an organisation sets
    `customRegistrationLocations` -- org 3 names the bundle's Village uuid -- a catchment on an
    invented type is not on the permitted list, so
    `getAddressLevelsForCatchmentAndMatchingAddressLevelTypeIds` returns empty and the server
    drops every entity keyed by `subjectTypeUuid` from syncDetails. `Encounter` is keyed on
    encounter type and survives, so the user still syncs something and the run looks ordinary.
    """
    sql = "\n".join(bu.statements(3, "cohort@org3", count=2))
    lookup = sql.index("customRegistrationLocations")
    invent = sql.index("insert into address_level_type")
    assert lookup < invent, "a permitted type must be resolved before one is invented"
    assert "order by alt.level" in sql, "deepest permitted type: a village, not a state"


def test_it_refuses_rather_than_inventing_a_type_under_a_registration_rule():
    """Inventing one would hand back a user whose Individual never syncs -- worse than no user,
    because the run completes and the result is wrong rather than absent."""
    sql = "\n".join(bu.statements(3, "cohort@org3"))
    assert "raise exception" in sql
    guard = sql.index("jsonb_array_length")
    assert guard < sql.index("insert into address_level_type")


def test_an_existing_bootstrap_location_is_repointed():
    """The location upsert finds it by uuid, so an organisation bootstrapped by the earlier
    version keeps the invented type and the failure with it. Without this the fix reaches only
    the organisations that never had the problem."""
    sql = "\n".join(bu.statements(3, "cohort@org3"))
    assert "update address_level set type_id = v_type_id" in sql
    assert "type_id is distinct from v_type_id" in sql


def test_every_find_is_scoped_to_the_organisation():
    """The uuids this file mints carry the organisation, so the uuid alone is unambiguous today.
    The guarantee lives in the values rather than the query, and `address_level_type` is where it
    would not hold: a bundle's uuids are reused in every organisation it is imported into, so the
    bundle's Village exists once per tenant with a different id each time."""
    sql = "\n".join(bu.statements(3, "cohort@org3"))
    finds = [l.strip() for l in sql.splitlines() if l.strip().startswith("select id into")]
    assert len(finds) >= 6, finds
    for line in finds:
        assert "organisation_id = 3" in line, line


def test_a_root_location_is_inserted_with_its_lineage_already_right():
    """**`address_level` carries a CHECK that a root's lineage equals its own id**, evaluated on
    the insert. This wrote `lineage = '0'` and corrected it on the next statement, which a CHECK
    never allows and PostgreSQL cannot defer -- so the whole transaction rolled back and nothing
    was written. The id comes from the sequence first instead."""
    sql = "\n".join(bu.statements(3, "cohort@org3"))
    assert "nextval(pg_get_serial_sequence('address_level', 'id'))" in sql
    insert = next(l for l in sql.splitlines() if "insert into address_level (" in l)
    assert insert.index("id,") < insert.index("lineage"), "the id is written, not left to default"
    values = sql[sql.index("insert into address_level ("):]
    values = values[values.index("values ("):values.index(";")]
    assert "v_loc_id::text" in values, "lineage must be the row's own id at insert time"
    assert "'0'" not in values, "the placeholder lineage is what the CHECK rejected"
    assert "parent_id" not in insert, "a root has no parent, which is the branch of the CHECK used"
