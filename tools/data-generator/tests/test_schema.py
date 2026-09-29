import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import schema


def test_every_table_the_loader_knows_has_a_contract():
    import copy_writer as cw
    assert set(cw.LOAD_ORDER) == set(schema.CONTRACTS)


def test_a_clean_target_verifies():
    for table, c in schema.CONTRACTS.items():
        schema.verify(table, sorted(c.accounted))


def test_a_new_nullable_column_is_refused_rather_than_left_null():
    """The one silent failure mode. sync_concept_1_value was exactly this: added by V1_208, indexed
    by sync_3 and sync_4, and a generator predating it would have loaded cleanly while producing
    data that never touched those paths."""
    cols = sorted(schema.CONTRACTS["individual"].accounted) + ["some_new_column"]
    with pytest.raises(schema.SchemaDrift, match="never heard of"):
        schema.verify("individual", cols)


def test_a_removed_column_is_reported():
    cols = [c for c in schema.CONTRACTS["individual"].accounted if c != "observations"]
    with pytest.raises(schema.SchemaDrift, match="no longer has"):
        schema.verify("individual", cols)


def test_both_problems_are_reported_together():
    c = schema.CONTRACTS["individual"]
    cols = [x for x in c.accounted if x != "observations"] + ["brand_new"]
    with pytest.raises(schema.SchemaDrift) as e:
        schema.verify("individual", cols)
    assert "never heard of" in str(e.value) and "no longer has" in str(e.value)


def test_every_table_is_reported_not_just_the_first():
    with pytest.raises(schema.SchemaDrift) as e:
        schema.verify_all({"individual": ["nope"], "encounter": ["also_nope"]})
    assert "individual" in str(e.value) and "encounter" in str(e.value)


def test_an_unknown_table_names_what_to_do():
    with pytest.raises(schema.SchemaDrift, match="Add one to schema.CONTRACTS"):
        schema.verify("group_subject", ["id"])


def test_every_unwritten_column_carries_a_reason():
    """'not needed' with no explanation is how a column that mattered gets waved through."""
    for table, c in schema.CONTRACTS.items():
        for col, reason in c.unwritten.items():
            assert len(reason) > 12, f"{table}.{col} needs a real reason, got {reason!r}"


def test_the_sync_columns_are_written_everywhere_they_exist():
    """sync_3 and sync_4 index these. A null keeps the generated data off those paths."""
    for table in ("individual", "program_enrolment", "program_encounter", "encounter"):
        c = schema.CONTRACTS[table]
        assert "sync_concept_1_value" in c.populated
        assert "sync_concept_2_value" in c.populated


def test_address_id_is_written_on_every_table_sync_1_indexes():
    for table in ("individual", "program_enrolment", "program_encounter", "encounter"):
        assert "address_id" in schema.CONTRACTS[table].populated


def test_the_migration_watermark_is_recorded():
    assert schema.CHECKED_AGAINST_MIGRATION.startswith("V1_")


def test_every_builder_emits_what_its_contract_claims():
    """The contract's `populated` set is a claim about the builder, and nothing checked it.

    It claimed `created_date_time` and `last_modified_date_time` for every audit-bearing table
    while four builders emitted neither. The columns are nullable, so `COPY` accepts the nulls —
    but each of those tables carries a BEFORE INSERT trigger that copies the timestamps into
    `audit`, whose own date columns are NOT NULL. The load fails with a message naming `audit`
    rather than the table being written, which is a long way from the cause.

    This is the offline half of validating against the real schema: it cannot see column types
    or triggers, but it can see that a builder does not produce what its contract promises.
    """
    import catchments as cat
    import deployment as dep
    import hierarchy as hy

    h = hy.build(1, 3)
    catchments, users = cat.plan(h)
    build = dep.build_tenant(dep.TenantSpec(name="t", organisation_id=1, field_workers=3), 0)

    emitted = {
        "catchment": cat.catchment_rows(catchments)[0],
        "users": cat.user_rows(users)[0],
        "groups": cat.group_rows([1])[0],
        "user_group": cat.user_group_rows(users)[0],
        "address_level": next(iter(dep.location_rows(build))),
        "catchment_address_mapping": cat.declared_mappings(catchments)[0],
    }
    for table, row in emitted.items():
        claimed = schema.CONTRACTS[table].populated
        missing = sorted(claimed - set(row))
        assert not missing, f"{table} contract claims {missing} but the builder emits none of them"


def test_the_target_check_catches_what_four_live_failures_taught_it():
    """`check_against_target` is the offline stand-in for a real database, so it has to catch the
    four shapes that got through every other test and failed on one.
    """
    target = {"t": [
        {"name": "id", "type": "integer", "required": False, "default": "nextval(...)"},
        {"name": "name", "type": "character varying", "required": True, "default": None},
        {"name": "created_date_time", "type": "timestamp", "required": True, "default": None},
    ]}

    # A column the target does not have — users.version, dropped by V1_42.
    assert any("no such column" in p for p in
               schema.check_against_target({"t": {"id": 1, "name": "x", "gone": 2,
                                                  "created_date_time": "2020-01-01"}}, target))
    # NOT NULL with no default and nothing writes it — users.name.
    assert any("nothing writes it" in p for p in
               schema.check_against_target({"t": {"id": 1, "created_date_time": "2020-01-01"}},
                                           target))
    # Written, but as null — the structural timestamps that fed a trigger into audit.
    assert any("written as null" in p for p in
               schema.check_against_target({"t": {"id": 1, "name": "x",
                                                  "created_date_time": None}}, target))
    # Too wide for the column — id is SERIAL, int4, whatever the Java entity says.
    assert any("exceeds int4" in p for p in
               schema.check_against_target({"t": {"id": 51_300_000_000, "name": "x",
                                                  "created_date_time": "2020-01-01"}}, target))
    # And a correct row is silent.
    assert schema.check_against_target(
        {"t": {"id": 1, "name": "x", "created_date_time": "2020-01-01"}}, target) == []


def _target():
    """The committed schema snapshot, if there is one."""
    import json
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / "columns.json"
    return json.loads(p.read_text()) if p.exists() else None


def test_every_builder_matches_the_real_schema():
    """The check that four rounds of live failures asked for, run offline.

    `columns.json` is a snapshot of the target's own `information_schema`, carrying each column's
    type, nullability and default. Every one of those four failures — a dropped column written, a
    NOT NULL column omitted, a NOT NULL column written as null, and an id too wide for int4 —
    is visible here without a database.
    """
    target = _target()
    if target is None:
        pytest.skip("no columns.json; run columns.sql against a target to enable this")

    import catchments as cat
    import deployment as dep
    import hierarchy as hy

    h = hy.build(1, 3)
    catchments, users = cat.plan(h)
    build = dep.build_tenant(dep.TenantSpec(name="t", organisation_id=1, field_workers=3), 0)
    builders = {
        "catchment": cat.catchment_rows(catchments)[0],
        "users": cat.user_rows(users)[0],
        "groups": cat.group_rows([1])[0],
        "user_group": cat.user_group_rows(users)[0],
        "address_level": next(iter(dep.location_rows(build))),
        "catchment_address_mapping": cat.declared_mappings(catchments)[0],
    }
    problems = schema.check_against_target(builders, target)
    assert not problems, "\n".join(problems)


def test_every_contract_accounts_for_the_columns_the_target_requires():
    """A NOT NULL column with no default that no contract mentions fails the load.

    Contract-level rather than builder-level, so it covers the transactional tables too — those
    need a bundle to produce a row, and this needs nothing.
    """
    target = _target()
    if target is None:
        pytest.skip("no columns.json; run columns.sql against a target to enable this")

    problems = []
    for table, cols in sorted(target.items()):
        c = schema.CONTRACTS.get(table)
        if c is None:
            problems.append(f"{table}: in the target, but no contract")
            continue
        names = {x["name"] for x in cols}
        for missing in sorted({x["name"] for x in cols if x["required"]} - c.accounted):
            problems.append(f"{table}.{missing}: NOT NULL with no default, unaccounted")
        for absent in sorted(c.populated - names):
            problems.append(f"{table}.{absent}: written, but the target has no such column")
    assert not problems, "\n".join(problems)
