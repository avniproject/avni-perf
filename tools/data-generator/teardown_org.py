"""Empty an organisation between scenarios, as SQL.

**Why this exists.** No run is read-only. Every sync ends with `POST /syncTelemetry`, so even a
pull-only scenario leaves a row per user per sync; a push scenario writes subjects, encounters and
enrolments with server-assigned ids; and every insert fires the `audit` trigger. `load.sql` is a
bare `BEGIN` plus `\\copy` with no truncate, so loading a second dataset onto a dirty organisation
fails on the primary key rather than doing anything useful.

**This is the iteration-phase reset, not the measurement-phase one.** Between the runs that produce
evidence, use G4's restore mechanism — `DELETE` leaves dead tuples, `VACUUM` will not shrink the
indexes, and successive runs stop resembling each other. That matters once F7 has passed and the
comparison is run against run. It does not matter while the generator is still changing, and a
restore is far too slow a loop for that. See docs/execution-plan.md, Day 9.

    python3 teardown_org.py --organisation 3 --id-base 1000000 > teardown.sql
    psql -d <db> -v ON_ERROR_STOP=1 -f teardown.sql

**Two scopes.** `--scope data` (the default) removes what the generator and the runs created and
leaves the bundle's metadata alone, so the next dataset can be loaded without re-importing concepts
and forms. `--scope all` empties every org-scoped table this script knows about, metadata included.

**`--id-base` is what keeps `data` scope honest.** Locations, catchments, groups and users are
shared between the bundle and the generator: the bundle's `locations.json` writes address levels,
and provisioning writes a `bundleloader@` user. Those live at ids the server assigned, while every
generated row sits at or above the dataset's `id_base` by construction. So structural tables are
cut by id range and purely transactional ones by organisation, because pushed rows carry
server-assigned ids outside any range.

**It refuses to run rather than half-work.** Before deleting anything it classifies every table
holding rows for the organisation into delete, keep, or unrecognised, and aborts on the third —
naming them. A teardown that silently leaves a table behind is the same failure as an import that
reports COMPLETED having brought nothing, and this repo has now had enough of those.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from copy_writer import LOAD_ORDER

# The organisation the server itself owns. `V0_3__CreateOpenCHSUser` seeds it along with user 1,
# self-referencing, before the audit constraints exist; every generated row's `created_by_id`
# points at that user. Emptying it breaks the deployment, not just the test data.
PROTECTED_ORGANISATIONS = (1,)

# Written by a run rather than by the generator, so they are cut by organisation: nothing here
# carries an id this tool can predict. Ordered children first.
#
# Over-listing is free — a table the schema does not have is skipped — while under-listing is
# caught by the preflight rather than silently leaving rows behind.
RUN_ARTEFACTS = (
    "sync_telemetry",
    "checklist_item",
    "checklist",
    "comment",
    "comment_thread",
    "entity_approval_status",
    "identifier_assignment",
    "individual_relationship",
    "group_subject",
    "subject_migration",
    "subject_program_eligibility",
)

# Cut by organisation: the generator writes these, and so does a push run, with ids the server
# assigned that no range would cover.
TRANSACTIONAL = ("encounter", "program_encounter", "program_enrolment", "individual")

# Cut by provenance under `data` scope, because the bundle writes into these too.
STRUCTURAL = ("user_group", "users", "groups", "catchment_address_mapping", "catchment",
              "address_level", "address_level_type")

# **What the generator wrote, identified by uuid rather than by id range.**
#
# The range cut is gone. It read `id >= id_base and id < GENERATED_ID_CEILING`, which assumed the
# application never allocates inside a band the generator reserves. It does: the generator writes
# explicit ids, an explicit id does not move the sequence, and so an organisation provisioned
# after a load was handed bundle `groups` ids from 1,000,004 upward -- inside the reserved range.
# A teardown of that organisation would have deleted its entire bundle group set as though the
# generator had written it.
#
# These uuids are deterministic and the application never produces them, so they say what a row's
# provenance is instead of guessing from where it landed. `load.sql` now also raises the sequences
# past the dataset, so the two work together: nothing collides, and what did come from the
# generator is recognisable.
#
# The contract this changes is worth stating: a teardown now removes rows by provenance. A row
# hand-written with a generator-shaped uuid is deleted; a generated row whose uuid was edited
# survives. That is a better basis than an id range, and it is a different one.
# `$1` is the organisation, bound at run time -- the script loops over organisations, so the
# pattern cannot be baked in when the SQL is written.
GENERATED_UUID = {
    "address_level": "uuid LIKE 'loc-' || $1 || '-%'",
    "catchment": "uuid LIKE 'catchment-' || $1 || '-%'",
    "users": "uuid LIKE 'user-' || $1 || '-%'",
    "groups": "uuid = 'group-' || $1",
    "user_group": "uuid LIKE 'usergroup-' || $1 || '-%'",
}

# `catchment_address_mapping` carries no uuid, and no id the generator populates -- load.sql
# copies only (catchment_id, addresslevel_id). It is reached through the catchments it points at,
# which are themselves identified by uuid.
VIA_PARENT = {
    "catchment_address_mapping":
        "catchment_id IN (SELECT id FROM catchment WHERE organisation_id = $1"
        " AND uuid LIKE 'catchment-' || $1 || '-%')",
}

# How a table is tied to an organisation, where it is not tied to one directly. `$1` is the
# organisation.
#
# **Not every table in the delete list has an `organisation_id`**, and the preflight cannot see
# the ones that do not: it discovers candidates by looking for that column, so a table scoped only
# through a parent is invisible to it and has to be named here. `catchment_address_mapping` is the
# case in hand — it carries `catchment_id` and `addresslevel_id` and nothing else identifying.
# Avni's own deleteOrgMetadata.sql scopes it the same way, through `catchment`.
ORG_PREDICATE = {
    "catchment_address_mapping":
        "catchment_id IN (SELECT id FROM catchment WHERE organisation_id = $1)",
}
DEFAULT_ORG_PREDICATE = "organisation_id = $1"

# The range cut is bounded above as well as below, so a bootstrap user survives a teardown.
# `bootstrap_user.py` places its rows at 2,100,000,000 — deliberately above anything generated but
# still inside int4 — and `environment-check.sh` needs that user to ask whether the environment is
# ready at all. A cut of `id >= id_base` alone would take it along with the dataset, and the next
# check would fail on a missing user rather than on anything real. `--scope all` still removes it.

# Left alone by `data` scope. Listed so the preflight can tell "deliberately kept" from "nobody has
# thought about this table", which is the distinction the whole check rests on.
METADATA = (
    "concept", "concept_answer", "form", "form_element", "form_element_group", "form_mapping",
    "subject_type", "operational_subject_type", "encounter_type", "operational_encounter_type",
    "program", "operational_program", "organisation_config", "identifier_source",
    "group_privilege", "privilege", "group_dashboard", "dashboard", "dashboard_section",
    "dashboard_filter", "dashboard_section_card_mapping", "report_card", "standard_report_card_type",
    "translation", "video", "checklist_detail", "checklist_item_detail", "individual_relation",
    "individual_relation_gender_mapping", "individual_relationship_type", "rule", "rule_dependency",
    "menu_item", "message_rule", "message_request_queue", "message_receiver", "task", "task_type",
    "task_status", "documentation", "documentation_item", "extension", "custom_query", "gender",
    # Location metadata, not dataset rows, on three independent readings: the generator never
    # writes it; the application maintains it when locations are created through
    # LocationMappingController, and the generator `\copy`s address_level straight past the app so
    # no mapping is produced; and Avni's own deleteOrgMetadata.sql groups it with the location
    # tables, deleting it immediately before address_level and address_level_type.
    #
    # If any row here did point at a generated address level, the address_level delete would fail
    # on the foreign key — safely, inside the transaction — and that would be the evidence for
    # moving it to STRUCTURAL with RANGE_COLUMN {"location_location_mapping": "location_id"}.
    "location_location_mapping",
)


def _quoted(pred: str) -> str:
    """A predicate embedded in a SQL string literal: every quote doubled."""
    return pred.replace("'", "''")


def _in_format(pred: str) -> str:
    """A predicate embedded in a `format()` template.

    **Two escapes, and missing either produces SQL that does not parse.** The quotes double
    because the predicate sits inside a string literal; the percents double because `format()`
    reads `%` as a placeholder, so a LIKE pattern's wildcard is one. The first version of the
    provenance cut escaped neither, and every structural delete was a syntax error:

        EXECUTE format('... uuid = 'group-' || $1', tbl)

    closes the literal at `'group-'` and leaves the rest as stray tokens.
    """
    return _quoted(pred).replace("%", "%%")


def _delete_order(scope: str) -> list[tuple[str, bool]]:
    """(table, cut_by_range) children first.

    The structural tail is `LOAD_ORDER` reversed, taken from the module that owns it rather than
    restated here, so a table added to the load cannot be forgotten by the teardown.
    """
    structural = [t for t in reversed(LOAD_ORDER) if t in STRUCTURAL]
    missing = set(STRUCTURAL) - set(structural)
    if missing:  # LOAD_ORDER changed under us; better to say so than to skip a table.
        raise ValueError(f"not in LOAD_ORDER, so the delete order is unknown: {sorted(missing)}")
    return ([(t, False) for t in RUN_ARTEFACTS]
            + [(t, False) for t in TRANSACTIONAL]
            + [(t, scope == "data") for t in structural])


def emit(organisations, id_base: int | None, scope: str) -> str:
    orgs = [organisations] if isinstance(organisations, int) else sorted(set(organisations))
    if not orgs:
        raise ValueError("no organisations to empty")
    protected = [o for o in orgs if o in PROTECTED_ORGANISATIONS]
    if protected:
        raise ValueError(
            f"organisation {protected[0]} is the server's own and is never emptied "
            f"(V0_3 seeds it with user 1, which every audit column references)")

    order = _delete_order(scope)
    known = sorted({t for t, _ in order} | (set(METADATA) if scope == "data" else set()))
    kept = sorted(set(METADATA) - {t for t, _ in order}) if scope == "data" else []

    out: list[str] = []
    w = out.append
    # id_base is accepted and recorded, not used: the cut is by provenance now. Kept in the
    # header because knowing which dataset a teardown was aimed at is worth having.
    named = (f"organisation {orgs[0]}" if len(orgs) == 1
             else f"{len(orgs)} organisations ({orgs[0]}..{orgs[-1]})")
    w(f"-- Empty {named} ({scope} scope)"
      + (f", generated rows at or above id {id_base}." if scope == "data" else "."))
    w("-- Generated by tools/data-generator/teardown_org.py. Run with:")
    w("--   psql -d <db> -v ON_ERROR_STOP=1 -f this-file.sql")
    w("--")
    w("-- One transaction: a teardown that stops halfway leaves an organisation that neither")
    w("-- loads nor runs, and works out slower than having done nothing.")
    w("BEGIN;")
    w("")
    w("DO $$")
    w("DECLARE")
    w(f"  orgs      int[] := ARRAY[{', '.join(str(o) for o in orgs)}];")
    w("  org       int;")
    w("  tbl       text;")
    w("  rng       boolean;")
    w("  col       text;")
    w("  n         bigint;")
    w("  total     bigint := 0;")
    w("  unknown   text[] := '{}';")
    w("  present   boolean;")
    w("BEGIN")
    w("  FOREACH org IN ARRAY orgs LOOP")
    w("  IF NOT EXISTS (SELECT 1 FROM organisation WHERE id = org) THEN")
    w("    RAISE EXCEPTION 'no organisation with id %', org;")
    w("  END IF;")
    w("")
    w("  -- Preflight. Every table carrying an organisation_id is classified before anything is")
    w("  -- deleted. A table holding rows for this organisation that is in neither list means the")
    w("  -- schema has moved and this script no longer knows what a full teardown is, so it stops")
    w("  -- instead of leaving rows behind under a success message.")
    w("  --")
    w("  -- `audit` shows up here on the first run if it is organisation-scoped. It is written by a")
    w("  -- BEFORE INSERT trigger on every table the generator loads, and is not in columns.json,")
    w("  -- so whether a teardown can reach its rows at all is genuinely unknown until this says.")
    w("  FOR tbl IN")
    w("    SELECT c.relname")
    w("      FROM pg_class c")
    w("      JOIN pg_namespace ns ON ns.oid = c.relnamespace")
    w("      JOIN pg_attribute a ON a.attrelid = c.oid")
    w("     WHERE c.relkind = 'r' AND ns.nspname = 'public'")
    w("       AND a.attname = 'organisation_id' AND a.attnum > 0 AND NOT a.attisdropped")
    w("  LOOP")
    w(f"    IF tbl <> ALL (ARRAY[{', '.join(repr(t) for t in known)}]::text[]) THEN")
    w("      EXECUTE format('SELECT EXISTS (SELECT 1 FROM %I WHERE organisation_id = $1)', tbl)")
    w("        INTO present USING org;")
    w("      IF present THEN unknown := unknown || tbl; END IF;")
    w("    END IF;")
    w("  END LOOP;")
    w("")
    w("  IF array_length(unknown, 1) > 0 THEN")
    w("    RAISE EXCEPTION 'these tables hold rows for organisation % and this script does not "
      "know whether to delete or keep them: %. Add each to TRANSACTIONAL, RUN_ARTEFACTS, "
      "STRUCTURAL or METADATA in teardown_org.py.', org, array_to_string(unknown, ', ');")
    w("  END IF;")
    w("")
    for table, by_provenance in order:
        pred = ORG_PREDICATE.get(table, DEFAULT_ORG_PREDICATE)
        if by_provenance:
            # `data` scope: only what the generator wrote. Identified by uuid, or through the
            # parent for the one table that has none.
            if table in VIA_PARENT:
                pred = VIA_PARENT[table]
            elif table in GENERATED_UUID:
                pred += f" AND {GENERATED_UUID[table]}"
            else:
                # Nothing here is the generator's. `address_level_type` is the case: it is in
                # LOAD_ORDER but the dataset takes the target's own types and writes none, so a
                # data-scope teardown has nothing to remove and must not guess.
                w(f"  -- {table}: the generator writes none of these, so --scope data skips it")
                continue
        w(f"  tbl := {table!r};")
        w("  IF to_regclass('public.' || tbl) IS NOT NULL THEN")
        w(f"    EXECUTE format('DELETE FROM %I WHERE {_in_format(pred)}', tbl)"
          " USING org;")
        w("    GET DIAGNOSTICS n = ROW_COUNT;")
        w("    total := total + n;")
        w("    IF n > 0 THEN RAISE NOTICE '  % rows from %', n, tbl; END IF;")
        w("  END IF;")
    w("")
    w("  END LOOP;")
    w(f"  RAISE NOTICE 'deleted % rows from % organisation(s)', total, {len(orgs)};")
    w("END $$;")
    w("")
    if kept:
        w("-- Kept, because --scope data leaves the bundle's metadata in place so the next dataset")
        w("-- can be loaded without re-importing it: " + ", ".join(kept[:8]) + ", and others.")
        w("")
    w("-- The count the next load depends on. `load.sql` has no truncate and no ON CONFLICT, so")
    w("-- anything left here surfaces as a primary key violation partway through a multi-hour")
    w("-- load rather than here, where it costs nothing.")
    w("DO $$")
    w("DECLARE n bigint; org int; left_over text[] := '{}';")
    w(f"  orgs int[] := ARRAY[{', '.join(str(o) for o in orgs)}];")
    w("BEGIN")
    w("  FOREACH org IN ARRAY orgs LOOP")
    # Unrolled rather than looped over a name array, because the organisation predicate differs
    # per table: `catchment_address_mapping` has no organisation_id of its own. A generic loop is
    # what put `WHERE organisation_id = $1` on a table that has no such column.
    for table, _ in order:
        pred = ORG_PREDICATE.get(table, DEFAULT_ORG_PREDICATE)
        w(f"    IF to_regclass('public.{table}') IS NOT NULL THEN")
        # A plain EXECUTE, not format(), so quotes double but percents must not.
        w(f"      EXECUTE 'SELECT count(*) FROM {table} WHERE {_quoted(pred)}'"
          " INTO n USING org;")
        w(f"      IF n > 0 THEN left_over := left_over || format('%s (%s)', {table!r}, n);"
          " END IF;")
        w("    END IF;")
    w("  END LOOP;")
    w("  IF array_length(left_over, 1) > 0 THEN")
    if scope == "data":
        w("    RAISE NOTICE 'still holding rows, which for --scope data is expected where the "
          "bundle wrote them: %', array_to_string(left_over, ', ');")
    else:
        w("    RAISE EXCEPTION '--scope all left rows behind: %', array_to_string(left_over, ', ');")
    w("  END IF;")
    w("END $$;")
    w("")
    w("COMMIT;")
    w("")
    w("-- Not covered here, and worth knowing before a run is trusted:")
    w("--   * `audit` grows with every insert and is not organisation-scoped unless the preflight")
    w("--     said otherwise. It is bloat, not correctness.")
    w("--   * media uploaded by a push run lives in S3 and survives this and any restore.")
    w("--   * dead tuples remain. That is fine while iterating and not fine between measured runs,")
    w("--     which is what G4's restore mechanism is for.")
    return "\n".join(out) + "\n"


def from_dataset(path: str | Path) -> tuple[list[int], int | None]:
    """The organisations and id floor of a dataset, from its recipe or its manifest.

    Both are accepted because both are to hand at different moments: the recipe is what was
    committed, the manifest is what a build actually produced and sits next to the `.tsv` files
    that were loaded. Reading either beats retyping the number, which is the one input here whose
    wrong values are quiet — too low takes the bundle's own locations and users along with the
    dataset, too high deletes nothing from the structural tables and surfaces hours into the next
    load as a primary key clash.
    """
    raw = json.loads(Path(path).read_text())
    if "tables" in raw or "provenance" in raw:  # a manifest
        target = raw.get("target") or {}
        if not target:
            raise ValueError(
                f"{path} was written before the manifest recorded its organisations and id_base. "
                f"Pass the recipe from datasets/ instead, or --organisation and --id-base.")
        return list(target.get("organisations") or []), target.get("id_base")
    if "tenants" in raw:  # a recipe
        return [t["organisation_id"] for t in raw["tenants"]], raw.get("id_base")
    raise ValueError(f"{path} is neither a dataset recipe nor a manifest")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dataset",
                   help="a recipe from datasets/ or a build's manifest.json. Supplies both the "
                        "organisations and the id_base, so neither has to be retyped")
    p.add_argument("--organisation", type=int, action="append", default=[],
                   help="an organisation to empty; never 1. Repeatable. Overrides --dataset")
    p.add_argument("--id-base", type=int,
                   help="the loaded dataset's id_base. Required for --scope data")
    p.add_argument("--scope", choices=("data", "all"), default="data",
                   help="data: generated rows and run artefacts, keeping the bundle's metadata "
                        "(default). all: every org-scoped table this script knows about")
    a = p.parse_args(argv)
    try:
        orgs, id_base = list(a.organisation), a.id_base
        if a.dataset:
            from_file_orgs, from_file_base = from_dataset(a.dataset)
            orgs = orgs or from_file_orgs
            if id_base is None:
                id_base = from_file_base
        if not orgs:
            raise ValueError("give --dataset, or --organisation at least once")
        sys.stdout.write(emit(orgs, id_base, a.scope))
    except (ValueError, OSError, json.JSONDecodeError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
