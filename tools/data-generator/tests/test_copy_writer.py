import json, sys, tempfile
from datetime import date, datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import copy_writer as cw
import schema


def unescape(s: str) -> str:
    """Undo `COPY ... FORMAT text` escaping, left to right.

    Sequential str.replace calls get this wrong: replacing `\\t` before `\\\\` turns an escaped
    backslash followed by a literal t into a tab. Postgres reads the stream once, so the test does
    too.
    """
    out, i = [], 0
    mapping = {"\\": "\\", "t": "\t", "n": "\n", "r": "\r"}
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            out.append(mapping.get(s[i + 1], s[i + 1]))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


# --- escaping ---------------------------------------------------------------

def test_backslash_is_escaped_before_everything_else():
    """Escaping the tab first would turn a literal backslash-t into a real tab on reload."""
    assert cw.escape("a\\tb") == "a\\\\tb"


@pytest.mark.parametrize("raw,expected", [
    ("plain", "plain"),
    ("with\ttab", r"with\ttab"),
    ("with\nnewline", r"with\nnewline"),
    ("with\rreturn", r"with\rreturn"),
    ("back\\slash", r"back\\slash"),
])
def test_control_characters_cannot_end_a_field_or_a_row(raw, expected):
    assert cw.escape(raw) == expected


def test_none_is_the_copy_null_and_not_an_empty_string():
    """An empty string and NULL are different values, and TEXT format distinguishes them."""
    assert cw.render(None) == r"\N"
    assert cw.render("") == ""


@pytest.mark.parametrize("value,expected", [
    (True, "t"), (False, "f"), (0, "0"), (-5, "-5"),
    (date(2026, 9, 18), "2026-09-18"),
])
def test_scalars_render_as_postgres_expects(value, expected):
    assert cw.render(value) == expected


def test_timestamps_render_with_a_space_separator():
    assert cw.render(datetime(2026, 9, 18, 7, 3, 1)) == "2026-09-18 07:03:01"


def test_observations_render_as_compact_jsonb():
    v = cw.render({"c-1": "a-1", "c-2": [1, 2]})
    assert json.loads(v) == {"c-1": "a-1", "c-2": [1, 2]}
    assert " " not in v, "spaces cost real bytes across millions of observation maps"


def test_a_tab_inside_an_observation_value_survives_both_layers():
    """Two escapings stack here. json.dumps turns a tab into backslash-t, then COPY escaping
    turns that backslash into two. Postgres unwraps one layer and the jsonb parser the other."""
    out = cw.render({"c-1": "free\ttext"})
    assert "\t" not in out, "a raw tab would end the field"
    assert json.loads(unescape(out)) == {"c-1": "free\ttext"}


def test_float_keeps_full_precision():
    assert float(cw.render(0.1 + 0.2)) == 0.1 + 0.2


# --- projection -------------------------------------------------------------

def test_values_are_laid_out_in_the_targets_column_order():
    row = {"b": 2, "a": 1}
    assert cw.project(row, ["a", "b"]) == ["1", "2"]
    assert cw.project(row, ["b", "a"]) == ["2", "1"]


def test_a_column_the_row_does_not_set_becomes_null():
    assert cw.project({"a": 1}, ["a", "b"]) == ["1", r"\N"]


def test_a_row_key_that_is_not_a_column_is_an_error():
    """The failure this prevents is the quiet one: a misspelt key would drop the value, and a
    schema that moved would shift every subsequent value one column left."""
    with pytest.raises(KeyError, match="not columns in the target"):
        cw.project({"a": 1, "typo": 2}, ["a", "b"], table="individual")


# --- files ------------------------------------------------------------------

def test_a_written_file_round_trips_through_the_copy_text_rules():
    d = Path(tempfile.mkdtemp())
    rows = [{"id": 1, "note": "has\ttab", "obs": {"k": "v"}, "gone": None},
            {"id": 2, "note": "has\nnewline", "obs": {}, "gone": True}]
    cols = ["id", "note", "obs", "gone"]
    assert cw.write_table(d / "t.tsv", rows, cols) == 2

    lines = (d / "t.tsv").read_text().splitlines()
    assert len(lines) == 2, "an escaped newline must not split the row"
    first = lines[0].split("\t")
    assert len(first) == len(cols)
    assert unescape(first[1]) == "has\ttab"
    assert json.loads(unescape(first[2])) == {"k": "v"}
    assert first[3] == r"\N"


def test_an_empty_table_writes_an_empty_file_rather_than_failing():
    d = Path(tempfile.mkdtemp())
    assert cw.write_table(d / "t.tsv", [], ["a"]) == 0
    assert (d / "t.tsv").read_text() == ""


# --- load script ------------------------------------------------------------

def test_tables_load_in_dependency_order():
    """A child row cannot reference a parent table loaded after it. And none of Avni's foreign keys
    are DEFERRABLE, so SET CONSTRAINTS ALL DEFERRED would not help — order is the only guard."""
    tables = {"encounter": ["id"], "individual": ["id"], "address_level": ["id"],
              "catchment": ["id"]}
    script = cw.load_script(tables, verify_schema=False)
    statements = [l.strip() for l in script.splitlines() if not l.strip().startswith("--")]
    assert "SET CONSTRAINTS ALL DEFERRED;" not in statements, \
        "it is a no-op against non-deferrable constraints and would imply order does not matter"
    pos = {t: script.index(f"copy {t} (") for t in tables}
    assert pos["address_level"] < pos["catchment"] < pos["individual"] < pos["encounter"]


def test_sequences_are_reset_because_copy_does_not_advance_them():
    """Ids are written explicitly so the generator can wire foreign keys — COPY would happily
    default them, but then nothing could reference the row. The cost is that the sequence is left
    behind, and the first application insert after a load collides on the primary key."""
    script = cw.load_script({"individual": ["id"]}, verify_schema=False)
    assert "setval(pg_get_serial_sequence('individual', 'id')" in script
    assert "MAX(id) FROM individual" in script


def test_the_load_is_one_transaction():
    script = cw.load_script({"individual": ["id"]}, verify_schema=False)
    assert script.index("BEGIN;") < script.index("copy individual") < script.index("COMMIT;")


def test_statistics_are_refreshed_after_the_load():
    script = cw.load_script({"individual": ["id"]}, verify_schema=False)
    assert script.index("COMMIT;") < script.index("ANALYZE;")


def test_the_script_uses_client_side_copy():
    """Server-side COPY FROM reads a path on the database host and needs superuser or
    pg_read_server_files. \\copy streams from wherever psql runs."""
    script = cw.load_script({"individual": ["id"]}, verify_schema=False)
    assert "\\copy individual" in script
    assert "\nCOPY individual" not in script


def test_the_script_names_every_column_explicitly():
    """Relying on table column order is how a schema change shifts every value silently."""
    script = cw.load_script({"individual": ["id", "uuid", "observations"]}, verify_schema=False)
    assert "\\copy individual (id, uuid, observations) FROM" in script


def test_a_table_outside_the_known_order_still_loads_last():
    script = cw.load_script({"individual": ["id"], "group_subject": ["id"]}, verify_schema=False)
    assert script.index("copy individual") < script.index("copy group_subject")


# --- schema drift -----------------------------------------------------------

def test_a_real_target_is_verified_against_the_contract():
    """The load refuses rather than warning. A warning in a load script is one nobody reads, and
    the failure it guards produces data that looks fine and measures the wrong thing."""
    cols = sorted(schema.CONTRACTS["individual"].accounted)
    cw.load_script({"individual": cols})          # verifies by default


def test_a_column_added_by_a_migration_stops_the_load():
    cols = sorted(schema.CONTRACTS["individual"].accounted) + ["sync_concept_3_value"]
    with pytest.raises(schema.SchemaDrift, match="never heard of"):
        cw.load_script({"individual": cols})


def test_a_table_with_no_contract_stops_the_load():
    with pytest.raises(schema.SchemaDrift, match="no contract for table"):
        cw.load_script({"group_subject": ["id"]})


def test_the_script_records_the_migration_it_was_checked_against():
    script = cw.load_script({"individual": sorted(schema.CONTRACTS["individual"].accounted)})
    assert schema.CHECKED_AGAINST_MIGRATION in script


def test_the_one_table_whose_id_nothing_references_leaves_it_to_the_sequence():
    """The explicit-id rule is applied per table, not blanket. catchment_address_mapping is the
    only table nothing points at, and schema.py records that as the reason."""
    c = schema.CONTRACTS["catchment_address_mapping"]
    assert "id" in c.unwritten
    assert "sequence" in c.unwritten["id"]
    for other in ("individual", "program_enrolment", "program_encounter", "encounter"):
        assert "id" in schema.CONTRACTS[other].populated
