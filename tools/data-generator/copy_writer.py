"""Write generated rows as PostgreSQL `COPY` input, and the script that loads them.

Plan H4 loads with `COPY` rather than through the API, which is orders of magnitude faster and the
only way millions of rows arrive in reasonable time. Three things that costs us, all handled here.

**The column list belongs to the database, not to this file.** Migrations accumulate, so a hardcoded
list would rot and produce a `COPY` that either fails or -- far worse -- shifts every value one
column to the left and loads silently. The caller supplies the column list, read from
`information_schema.columns` on the target, and rows are projected onto it. A row key that is not a
column is an error rather than a value quietly dropped.

**Ids are written explicitly, which costs a `setval`.** `COPY` applies a column's default for any
column left out of its list, so omitting `id` would let the sequence assign it -- but then nothing
could reference the row. The generator has to write `program_enrolment.individual_id` and
`program_encounter.program_enrolment_id`, and it cannot know an id the database is about to choose.
The alternatives are both worse than the tax: reading ids back mid-generation needs a round trip
that streaming to disk exists to avoid, and resolving them afterwards means an `UPDATE ... SET
individual_id = (SELECT id FROM individual WHERE uuid = ...)` per child table across millions of
rows, which costs more than the `COPY` it supports.

The rule is applied per table rather than blanket: `catchment_address_mapping.id` is left to the
sequence, because nothing references it. It is the only one.

So `COPY` does not advance the sequences it bypassed, and the first application insert after a load
would collide on the primary key. `load_script` emits a `setval` per table to close that.

**TEXT format has its own escaping.** A tab or newline inside a value ends the field or the row, so
backslash, tab, newline and carriage return are escaped, and NULL is `\\N` -- which is why the
backslash has to be escaped first.

**Load order is load-bearing.** None of Avni's foreign keys are declared `DEFERRABLE`, so
`SET CONSTRAINTS ALL DEFERRED` achieves nothing and a child row loaded before its parent fails on
the spot. `LOAD_ORDER` is the only thing preventing that.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import schema
from schema import column_names

NULL = r"\N"

# Order matters: a row cannot reference a table loaded after it.
LOAD_ORDER = (
    "address_level_type",
    "address_level",
    "catchment",
    "catchment_address_mapping",
    # `groups` before `users` only for readability; it references nothing but the organisation.
    # `user_group` must follow both, since it references each.
    "groups",
    "users",
    "user_group",
    "individual",
    "program_enrolment",
    "program_encounter",
    "encounter",
)


def escape(value: str) -> str:
    """Escape one value for `COPY ... FORMAT text`. Backslash first, or the rest double-escape."""
    return (value.replace("\\", "\\\\")
                 .replace("\t", "\\t")
                 .replace("\n", "\\n")
                 .replace("\r", "\\r"))


def render(value) -> str:
    """One Python value as its `COPY` text representation."""
    if value is None:
        return NULL
    if isinstance(value, bool):
        return "t" if value else "f"
    if isinstance(value, (int, Decimal)):
        return str(value)
    if isinstance(value, float):
        # repr keeps full precision; str() rounds in older versions.
        return repr(value)
    if isinstance(value, datetime):
        return escape(value.isoformat(sep=" "))
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        # jsonb. separators drop the spaces json.dumps adds by default, which is a real saving
        # across millions of observation maps.
        return escape(json.dumps(value, separators=(",", ":"), default=str))
    return escape(str(value))


def project(row: Mapping, columns: Sequence, *, table: str = "") -> list[str]:
    """Lay a row out in the target's column order, refusing keys that are not columns.

    Takes either shape of `columns.json` — a list of names, or the richer list of dicts that
    carries type and nullability — because COPY only ever needed the names and order.
    """
    columns = schema.column_names(columns)
    unknown = set(row) - set(columns)
    if unknown:
        where = f" for {table}" if table else ""
        raise KeyError(
            f"row keys{where} are not columns in the target: {sorted(unknown)}. "
            f"Either the schema moved or a name is misspelt -- both would otherwise load silently."
        )
    return [render(row.get(c)) for c in columns]


def written_columns(columns: Sequence, row: Mapping) -> list[str]:
    """The target's columns, in its order, narrowed to the ones this row actually populates.

    **A column the generator does not populate must be left out of the COPY list entirely, not
    written as `\\N`.** COPY treats `\\N` as an explicit NULL and never consults the column's
    default, so a NOT NULL column with a default fails the load, and a nullable one with a
    default gets NULL instead of the default. The second is the dangerous shape:
    `organisation_id` defaults to 1, so a row that skipped it would load cleanly into the wrong
    tenant rather than erroring.

    Leaving the column out instead lets the server's own default apply — which is the right
    behaviour for `is_voided`, `catchment.type`, `address_level_type.uuid` and the rest — while a
    NOT NULL column with no default still fails loudly, as it should.
    """
    return [c for c in column_names(columns) if c in row]


def write_table(path: Path, rows: Iterable[Mapping], columns: Sequence,
                *, table: str = "") -> tuple[int, list[str]]:
    """Write one table's `COPY` file. Returns the row count and the columns written.

    The caller needs the column list back, because the `\copy` statement has to name exactly
    these and no others.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    written: list[str] = []
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            if not written:
                written = written_columns(columns, row)
            fh.write("\t".join(project(row, written, table=table or path.stem)))
            fh.write("\n")
            n += 1
    return n, (written or column_names(columns))


def load_script(tables: Mapping[str, Sequence[str]], *, directory: str = ".",
                serial_tables: Iterable[str] | None = None,
                build_indexes_after: bool = True,
                verify_schema: bool = True) -> str:
    """The SQL that loads the written files, in dependency order.

    Verifies the target's columns against `schema.CONTRACTS` first, so a migration that added a
    column the generator should be writing stops the load rather than loading a silent NULL.
    `verify_schema=False` is for tests using synthetic tables.

    Index creation is left to the caller's own DDL: H4 builds indexes after the load, and G4
    requires them to match production's definitions exactly, so they are not invented here.
    """
    if verify_schema:
        schema.verify_all(dict(tables))

    ordered = [t for t in LOAD_ORDER if t in tables] + \
              [t for t in tables if t not in LOAD_ORDER]
    serials = set(serial_tables if serial_tables is not None else ordered)

    out = [
        "-- Generated by tools/data-generator. Loads one dataset.",
        f"-- Schema contract checked against Flyway {schema.CHECKED_AGAINST_MIGRATION}.",
        "-- Run with psql:  psql -d <db> -v ON_ERROR_STOP=1 -f load.sql",
        "--",
        "-- \\copy, not COPY: server-side COPY FROM reads a path on the database host and needs",
        "-- superuser or pg_read_server_files. \\copy streams the file from wherever psql runs.",
        "--",
        "-- Load order is load-bearing. None of Avni's foreign keys are declared DEFERRABLE, so",
        "-- SET CONSTRAINTS ALL DEFERRED would do nothing here and a child row loaded before its",
        "-- parent fails immediately.",
        "--",
        "-- **Notices off, because the audit trigger raises two per row.** Every insert logs",
        "-- `Checking sync disabled value...` and `setting value of audit to N`, each formatted by",
        "-- the server and sent to the client. On a day-180 tenant that is about 4.6 million lines",
        "-- of it, inside the phase being timed -- so leaving it on does not just clutter the log,",
        "-- it inflates the load measurement G4's cadence is derived from. Nothing about what gets",
        "-- loaded changes; warnings and errors still arrive.",
        "SET client_min_messages = warning;",
        "BEGIN;",
        "",
    ]
    for t in ordered:
        cols = ", ".join(schema.column_names(tables[t]))
        out += [f"\\echo loading {t}",
                f"\\copy {t} ({cols}) FROM '{directory}/{t}.tsv' WITH (FORMAT text)",
                ""]

    if serials:
        out += ["-- COPY does not advance a sequence, so the first application insert after this",
                "-- load would collide on the primary key.", ""]
        for t in ordered:
            if t in serials:
                out.append(
                    f"SELECT setval(pg_get_serial_sequence('{t}', 'id'), "
                    f"COALESCE((SELECT MAX(id) FROM {t}), 1));")
        out.append("")

    out += ["COMMIT;", ""]

    # **Raise every sequence past what was just loaded.**
    #
    # The generator writes explicit ids, and an explicit id does not move the sequence. So after a
    # load the application still allocates from wherever the sequence was -- which is *inside* the
    # band the dataset occupies. That is not theoretical: organisations provisioned after a load
    # were given bundle `groups` ids from 1,000,004 upward, inside the range the generator reserved
    # for itself, and the next load then failed on the primary key against a row the application
    # owned.
    #
    # A reserved band cannot be defended by convention, only by moving the sequence. After this
    # the application always allocates above the dataset instead of into it.
    #
    # `greatest` because a sequence is never lowered: another tenant may already have pushed it
    # higher, and winding it back would hand out ids that are already taken.
    out += [
        "-- Move the sequences above the ids just loaded, so the application allocates after the",
        "-- dataset rather than into it. See the comment in copy_writer.load_script.",
        "--",
        "-- Notices back on: this block's are the record of what it changed, and a load that",
        "-- raised nothing here would mean the sequences were already above the dataset.",
        "SET client_min_messages = notice;",
        "DO $$",
        "DECLARE tbl text; seq text; loaded bigint; current_pos bigint;",
        "BEGIN",
        f"  FOREACH tbl IN ARRAY ARRAY[{', '.join(repr(t) for t in ordered)}]::text[] LOOP",
        "    seq := pg_get_serial_sequence(tbl, 'id');",
        "    IF seq IS NULL THEN CONTINUE; END IF;   -- no id column, or not sequence-backed",
        "    EXECUTE format('SELECT coalesce(max(id), 0) FROM %I', tbl) INTO loaded;",
        "    EXECUTE format('SELECT last_value FROM %s', seq) INTO current_pos;",
        "    IF loaded > current_pos THEN",
        "      PERFORM setval(seq, loaded);",
        "      RAISE NOTICE '  % -> %', seq, loaded;",
        "    END IF;",
        "  END LOOP;",
        "END $$;",
        "",
    ]
    if build_indexes_after:
        out += ["-- Build indexes and refresh statistics after the load, not before (H4).",
                "-- The index definitions are production's own and belong with the schema.",
                "ANALYZE;", ""]
    return "\n".join(out)
