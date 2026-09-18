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
