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


def test_data_scope_no_longer_needs_an_id_base():
    """It used to, because the cut was a range. Provenance replaced it, so the base is optional.

    A range cut assumed the application never allocates inside a band the generator reserves,
    which turned out to be false: organisations provisioned after a load were given bundle
    `groups` ids from 1,000,004 upward, and a teardown would have deleted them.
    """
    td.emit([3], None, "data")
    td.emit([3], None, "all")


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


def test_run_artefacts_go_first_because_they_reference_the_subjects():
    """A pull-only run still writes sync_telemetry, and a push run leaves rows pointing at
    subjects. Deleting individuals first would fail on the foreign key."""
    s = sql()
    for table in ("sync_telemetry", "identifier_assignment", "entity_approval_status"):
        assert position(s, table) < position(s, "individual")


def test_every_loaded_table_is_accounted_for():
    """A table added to the load and forgotten by the reset means the next load dies on a primary
    key partway through, hours in. Accounted for means deleted, or named as deliberately skipped:
    the generator takes the target's own `address_level_type` rows and writes none."""
    s = sql()
    for table in LOAD_ORDER:
        assert f"tbl := {table!r};" in s or f"-- {table}: the generator writes none" in s, (
            f"{table} is loaded but neither removed nor explained")


def test_structural_tables_are_cut_by_provenance_and_transactional_ones_by_organisation():
    """The bundle writes locations, catchments, groups and a bundleloader user into the same
    tables the generator does, so those need telling apart. Pushed rows carry ids and uuids the
    server assigned, so they can only go by organisation."""
    s = sql()

    def statement(table):
        body = s[position(s, table):]
        return body[:body.index("GET DIAGNOSTICS")]

    for table, mark in (("users", "uuid LIKE ''user-''"),
                        ("groups", "uuid = ''group-''"),
                        ("catchment", "uuid LIKE ''catchment-''"),
                        ("address_level", "uuid LIKE ''loc-''"),
                        ("user_group", "uuid LIKE ''usergroup-''")):
        assert mark in statement(table), f"{table} should be cut by its generated uuid"
    for table in ("individual", "encounter", "sync_telemetry"):
        assert "uuid" not in statement(table), f"{table} should be cut by organisation alone"


def test_the_join_table_is_cut_through_its_catchment():
    """It carries no uuid, and no id the generator populates -- load.sql copies only
    (catchment_id, addresslevel_id). So it is reached through the catchments it points at, which
    are themselves identified by uuid."""
    s = sql()
    body = s[position(s, "catchment_address_mapping"):][:400]
    assert "catchment_id IN (SELECT id FROM catchment" in body
    assert "uuid LIKE ''catchment-''" in body


def test_a_bootstrap_user_survives_a_teardown():
    """environment-check.sh needs a user to ask anything at all, and a bootstrap one is not the
    generator's. Its uuid is `bootstrap-user-{org}`, which no generated pattern matches, so it
    survives without needing an id band to hide in -- which is what the old upper bound was for.
    """
    s = sql()
    assert "uuid LIKE ''user-'' || $1 || ''-%%''" in s
    assert "bootstrap" not in s.lower() or "GENERATED_ID_CEILING" not in s
    assert "id_floor" not in s and "bootstrap_floor" not in s


def test_scope_all_ignores_provenance_entirely():
    """`all` means empty the organisation, bundle rows included, so nothing is filtered by uuid."""
    s = sql(scope="all")
    assert "uuid LIKE" not in s and "uuid = ''group-''" not in s
    assert "tbl := 'address_level_type';" in s, "skipped under data scope, removed under all"


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


def test_location_mappings_are_kept_not_deleted():
    """Found by the preflight on the first real run against org 3, which refused to delete
    anything rather than guess.

    `location_location_mapping` is location metadata the application maintains through
    LocationMappingController. The generator never writes it — it `\\copy`s address_level straight
    past the application — and Avni's own deleteOrgMetadata.sql groups it with the location tables.
    """
    s = sql()
    assert "tbl := 'location_location_mapping';" not in s
    assert "location_location_mapping" in td.METADATA
    # It has to be in the known set, or the preflight aborts on it again.
    assert "'location_location_mapping'" in s


def test_a_table_with_no_organisation_id_is_scoped_through_its_parent():
    """`catchment_address_mapping` carries (id, catchment_id, addresslevel_id) and nothing else.

    The first delete phase to reach it failed on `column "organisation_id" does not exist`. It is
    invisible to the preflight too, which finds candidates *by* that column, so a table scoped
    only through a parent has to be named. Avni's deleteOrgMetadata.sql scopes it the same way.
    """
    s = sql()
    body = s[position(s, "catchment_address_mapping"):][:600]
    assert "catchment_id IN (SELECT id FROM catchment WHERE organisation_id = $1" in body
    assert "catchment_address_mapping WHERE organisation_id" not in s


def test_the_leftover_check_uses_the_same_predicates_as_the_delete():
    """It used to loop over a name array with `WHERE organisation_id = $1` hardcoded, which is
    the same defect one statement further down: it would have failed after a successful delete."""
    s = sql()
    for table in ("catchment_address_mapping", "individual", "users"):
        assert f"SELECT count(*) FROM {table} WHERE" in s
    assert ("SELECT count(*) FROM catchment_address_mapping WHERE catchment_id IN "
            "(SELECT id FROM catchment WHERE organisation_id = $1)") in s


def test_every_deleted_table_has_a_scoping_predicate():
    """Over-listing ORG_PREDICATE is harmless; a missing entry is a runtime error against a live
    database, which is the most expensive place to find one."""
    for table, _ in td._delete_order("data"):
        pred = td.ORG_PREDICATE.get(table, td.DEFAULT_ORG_PREDICATE)
        assert "$1" in pred, f"{table} has no organisation placeholder"


def test_every_dynamic_statement_is_escaped_so_it_parses():
    """The provenance cut embeds predicates containing quotes and LIKE wildcards into dynamic
    SQL, and there are two different escapes depending on where they land.

    Inside `format()` both apply: quotes double because the predicate sits in a string literal,
    and percents double because `format()` reads `%` as a placeholder. Inside a plain `EXECUTE`
    only the quotes do. The first version escaped neither, so every structural delete was a
    syntax error — `uuid = 'group-' || $1` closes the enclosing literal at `'group-'`. It was
    caught by a reader before it ran, which is not a check.
    """
    import re
    for scope in ("data", "all"):
        for raw in td.emit([10], None, scope).splitlines():
            line = raw.strip()
            if line.startswith("--") or "EXECUTE" not in line:
                continue
            assert line.count("'") % 2 == 0, f"unbalanced quotes: {line}"
            if "EXECUTE format(" in line:
                for m in re.finditer(r"%(.)", line):
                    assert m.group(1) in "I%sL", f"bare % in a format template: {line}"


def test_the_generated_uuid_patterns_survive_escaping_intact():
    """Escaping must not change what the SQL matches. Doubling turns `'loc-'` into `''loc-''`,
    which Postgres reads back as `'loc-'`; getting it wrong silently matches nothing and a
    teardown would report success having deleted no generated rows."""
    s = sql()
    for pattern in ("''loc-'' || $1 || ''-%%''",
                    "''catchment-'' || $1 || ''-%%''",
                    "''user-'' || $1 || ''-%%''",
                    "''usergroup-'' || $1 || ''-%%''",
                    "''group-'' || $1"):
        assert pattern in s, f"missing or mis-escaped: {pattern}"
