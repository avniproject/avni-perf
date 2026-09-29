import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import bootstrap_user as boot
import teardown_org as td
from copy_writer import LOAD_ORDER


def sql(organisation=3, id_base=1_000_000, scope="data"):
    return td.emit([organisation], id_base, scope)


def position(s, table):
    """Where a table's delete statement sits in the emitted script."""
    marker = f"tbl := {table!r};"
    assert marker in s, f"{table} is never deleted"
    return s.index(marker)


def test_organisation_one_is_refused():
    """V0_3 seeds organisation 1 with user 1, self-referencing, before the audit constraints.

    Every generated row's created_by_id points at that user, so emptying it does not break the
    test data, it breaks the deployment.
    """
    with pytest.raises(ValueError, match="never emptied"):
        sql(organisation=1)


def test_data_scope_will_not_run_without_an_id_base():
    """Without it the cut cannot tell a generated location from one the bundle imported.

    Deleting every address_level in the organisation would take the bundle's 15 locations with
    the dataset's 7, and the next run would need a re-import to explain why nothing syncs.
    """
    with pytest.raises(ValueError, match="--id-base is required"):
        td.emit([3], None, "data")
    td.emit([3], None, "all")  # `all` is explicit about wanting that, so it needs no base.


def test_children_are_deleted_before_their_parents():
    """None of Avni's foreign keys are DEFERRABLE, so order is load-bearing here as in load.sql."""
    s = sql()
    assert position(s, "encounter") < position(s, "individual")
    assert position(s, "program_encounter") < position(s, "program_enrolment")
    assert position(s, "program_enrolment") < position(s, "individual")
    assert position(s, "individual") < position(s, "address_level")
    assert position(s, "user_group") < position(s, "users")
    assert position(s, "user_group") < position(s, "groups")
    assert position(s, "users") < position(s, "catchment")
    assert position(s, "catchment_address_mapping") < position(s, "catchment")
    assert position(s, "catchment_address_mapping") < position(s, "address_level")
    assert position(s, "address_level") < position(s, "address_level_type")


def test_run_artefacts_go_first_because_they_reference_the_subjects():
    """A pull-only run still writes sync_telemetry, and a push run leaves rows pointing at
    subjects. Deleting individuals first would fail on the foreign key."""
    s = sql()
    for table in ("sync_telemetry", "identifier_assignment", "entity_approval_status"):
        assert position(s, table) < position(s, "individual")


def test_every_loaded_table_is_also_torn_down():
    """The failure this guards against is a table added to the load and forgotten by the reset:
    the next load then dies on a primary key partway through, hours in."""
    s = sql()
    for table in LOAD_ORDER:
        assert f"tbl := {table!r};" in s, f"{table} is loaded but never removed"


def test_structural_tables_are_cut_by_range_and_transactional_ones_by_organisation():
    """The bundle writes locations, catchments, groups and a bundleloader user into the same
    tables the generator does. Pushed rows, by contrast, carry ids the server assigned, which no
    range covers — so those have to go by organisation."""
    s = sql()
    def line(table):
        return s[position(s, table):].splitlines()[0]
    for table in ("users", "groups", "catchment", "address_level", "catchment_address_mapping"):
        assert "rng := true" in line(table), f"{table} should be cut by id range"
    for table in ("individual", "encounter", "sync_telemetry"):
        assert "rng := false" in line(table), f"{table} should be cut by organisation"


def test_the_join_table_is_cut_through_its_catchment():
    """catchment_address_mapping is a bare join table with no id of its own, so naming `id`
    would be a runtime error rather than a no-op."""
    s = sql()
    assert "col := 'catchment_id'" in s[position(s, "catchment_address_mapping"):][:200]


def test_a_bootstrap_user_survives_a_teardown():
    """environment-check.sh needs a user to ask anything at all, and bootstrap_user.py puts one
    above every generated id. A cut of `id >= id_base` alone would take it, and the next check
    would fail on a missing user rather than on anything real."""
    s = sql()
    assert str(boot.BOOTSTRAP_ID_BASE) in s
    assert "AND %I >= $2 AND %I < $3" in s
    assert "USING org, id_floor, bootstrap_floor;" in s


def test_scope_all_ignores_the_range_entirely():
    s = sql(scope="all")
    assert "rng := true" not in s
    assert "bootstrap_floor" in s  # declared, but no range delete uses it


def test_it_aborts_on_a_table_it_does_not_recognise():
    """The preflight is the difference between a reset and a reset that looks like one.

    `audit` is the live example: it is written by a BEFORE INSERT trigger on every table the
    generator loads and is absent from columns.json, so whether a teardown can reach it is not
    known until this reports.
    """
    s = sql()
    assert "RAISE EXCEPTION 'these tables hold rows for organisation %" in s
    assert "does not know whether to delete or keep them" in s
    # It has to look at what is actually in the schema, not at a list written here.
    assert "pg_attribute" in s and "a.attname = 'organisation_id'" in s
    # And only tables that actually hold rows for this organisation should stop the run.
    assert "SELECT EXISTS (SELECT 1 FROM %I WHERE organisation_id = $1)" in s


def test_scope_all_fails_if_anything_is_left_behind():
    """`data` scope expects leftovers — the bundle's rows are the point of keeping them — so only
    `all` can treat a remaining row as a failure."""
    assert "RAISE EXCEPTION '--scope all left rows behind" in sql(scope="all")
    assert "RAISE EXCEPTION '--scope all left rows behind" not in sql(scope="data")
    assert "still holding rows" in sql(scope="data")


def test_it_is_one_transaction():
    """A teardown that stops halfway leaves an organisation that neither loads nor runs."""
    s = sql()
    assert s.index("BEGIN;") < s.index("tbl := 'sync_telemetry';") < s.rindex("COMMIT;")


def test_the_delete_order_notices_if_load_order_moves(monkeypatch):
    """STRUCTURAL is ordered by reading LOAD_ORDER rather than by restating it. If a table stops
    appearing there the order is no longer known, and guessing is what this repo keeps paying for.
    """
    monkeypatch.setattr(td, "LOAD_ORDER", tuple(t for t in LOAD_ORDER if t != "users"))
    with pytest.raises(ValueError, match="not in LOAD_ORDER"):
        td._delete_order("data")


def test_metadata_is_kept_under_data_scope_and_named_as_kept():
    """Re-importing a bundle is minutes of Spring Batch; keeping it is why `data` scope exists."""
    s = sql()
    for table in ("concept", "form_mapping", "subject_type", "encounter_type"):
        assert f"tbl := {table!r};" not in s, f"{table} should survive a data-scope teardown"
    assert "Kept, because --scope data leaves the bundle's metadata in place" in s


def test_metadata_and_delete_lists_do_not_overlap():
    """A table in both lists would be deleted while the header claims it was kept."""
    deleted = {t for t, _ in td._delete_order("data")}
    assert not deleted & set(td.METADATA)


# --- where the id_base comes from -------------------------------------------------------------
#
# The number itself is the weak point of the whole tool. Too low and the structural cut takes the
# bundle's locations, catchments and bundleloader user along with the dataset; too high and it
# deletes nothing there, which surfaces as a primary key violation hours into the next load. So it
# is read from the dataset rather than retyped.

def test_a_recipe_supplies_both_the_organisations_and_the_floor(tmp_path):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"name": "x", "id_base": 1_000_000,
                             "tenants": [{"organisation_id": 3}, {"organisation_id": 4}]}))
    assert td.from_dataset(f) == ([3, 4], 1_000_000)


def test_a_manifest_supplies_them_too(tmp_path):
    """The manifest sits next to the .tsv files that were loaded, which is the thing being undone."""
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps({"recipe": "x", "tables": {},
                             "target": {"organisations": [7], "id_base": 5_000_000}}))
    assert td.from_dataset(f) == ([7], 5_000_000)


def test_a_manifest_from_before_the_field_existed_says_so(tmp_path):
    """Rather than reporting the file as unrecognised, which sends you looking at the wrong thing."""
    f = tmp_path / "manifest.json"
    f.write_text(json.dumps({"recipe": "x", "tables": {}, "provenance": {}}))
    with pytest.raises(ValueError, match="written before the manifest recorded"):
        td.from_dataset(f)


def test_something_that_is_neither_is_rejected(tmp_path):
    f = tmp_path / "x.json"
    f.write_text(json.dumps({"hello": "world"}))
    with pytest.raises(ValueError, match="neither a dataset recipe nor a manifest"):
        td.from_dataset(f)


def test_the_co_tenant_case_empties_every_tenant_in_one_script():
    """513 organisations, one id_base. Emitting per-organisation scripts would be 513 files and
    513 chances to run a different subset than was loaded."""
    s = td.emit(list(range(100, 130)), 1_000_000, "data")
    assert "ARRAY[100, 101, 102" in s
    assert "FOREACH org IN ARRAY orgs LOOP" in s
    assert s.count("tbl := 'individual';") == 1  # the loop, not the statements, repeats
    assert "30 organisations (100..129)" in s


def test_a_protected_organisation_anywhere_in_the_list_stops_it():
    with pytest.raises(ValueError, match="never emptied"):
        td.emit([3, 1, 4], 1_000_000, "data")


def test_organisations_are_deduplicated_and_ordered():
    s = td.emit([5, 3, 5], 1_000_000, "data")
    assert "ARRAY[3, 5]" in s
