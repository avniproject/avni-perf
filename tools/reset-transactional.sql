-- G4's per-run reset: empty the transactional tables and the audit rows they created.
--
--   psql -d <db> -v ON_ERROR_STOP=1 -f tools/reset-transactional.sql
--   psql -d <db> -v ON_ERROR_STOP=1 -f <dataset>/reload.sql      -- for every dataset, after
--
-- **`audit` is not in the TRUNCATE list, and must never be.** It looks like it belongs there: a
-- BEFORE INSERT trigger on 63 tables writes one `audit` row per inserted row, so a 2.3M-row load
-- creates 2.3M audit rows, the TRUNCATE orphans them, and the next cycle adds 2.3M more. That is
-- the growth this file exists to stop. But 42 foreign keys reference `audit(id)`, and they are not
-- the transactional tables -- they are `concept`, `form`, `form_element`, `form_mapping`,
-- `subject_type`, `address_level`, `organisation_config` and the rest of the metadata. `TRUNCATE
-- audit CASCADE` empties every one of them, and `reload.sql` restores only transactional rows, so
-- the organisation would need re-provisioning from its bundle. The blast radius is the whole
-- schema and the command that causes it is two words longer than the safe one.
--
-- So the orphans are deleted rather than truncated, and deleted by provenance: the audit ids held
-- by the tables this script is about to empty, captured before they are emptied, because
-- afterwards nothing records which rows they were.
--
-- **Why the referential integrity checks are turned off for that delete.** Every one of those 42
-- foreign keys is NO ACTION with no index on the referencing `audit_id` column. Deleting a
-- referenced row therefore costs one *sequential scan per constraint per row* -- 2.3M rows times
-- 42 unindexed scans, which is not slow but infeasible. `session_replication_role = replica`
-- suppresses the checks, and it is safe here for a specific reason rather than a general one:
-- the rows being deleted are exactly those whose owning tables the TRUNCATE on the line above has
-- just emptied, so by construction nothing references them. That argument holds only while the
-- capture set is the TRUNCATE's own cascade closure, which is why the closure is computed from
-- the catalogue below rather than listed here.
--
-- **The delete does not shrink the table, and does not need to.** It leaves dead tuples that the
-- following VACUUM marks reusable, so the next cycle's inserts refill them. Steady state, not
-- zero -- which is what "stops growing" means here.

\set ON_ERROR_STOP on
\timing on

BEGIN;

-- Fail before the expensive part rather than after it. On RDS this needs `rds_superuser`; if the
-- role cannot be set, nothing below has run yet and nothing has been emptied.
SET LOCAL session_replication_role = replica;

CREATE TEMP TABLE doomed_audit (id bigint) ON COMMIT DROP;

DO $reset$
DECLARE
    closure  text[];
    carriers text[];
    tbl      text;
    n        bigint;
    total    bigint := 0;
    -- Tables a reset must leave standing. They are not a wish list: `reload.sql` carries only the
    -- transactional rows, so anything here that CASCADE reached would be gone until the
    -- organisation was provisioned again from its bundle.
    survives text[] := ARRAY[
        'audit', 'organisation', 'organisation_config', 'users', 'user_group', 'groups',
        'address_level', 'address_level_type', 'catchment', 'catchment_address_mapping',
        'concept', 'concept_answer', 'form', 'form_element', 'form_element_group', 'form_mapping',
        'subject_type', 'program', 'encounter_type', 'operational_subject_type',
        'operational_program', 'operational_encounter_type'];
    breached text[];
BEGIN
    -- What TRUNCATE ... CASCADE will actually empty: the four named tables, plus everything that
    -- references them, transitively. Read from pg_constraint rather than restated here, because a
    -- restated list cannot notice a foreign key somebody adds next release.
    --
    -- Assigned with ARRAY(...) rather than SELECT ... INTO: plpgsql finds INTO by scanning the
    -- statement, and a leading WITH RECURSIVE is exactly the shape worth not relying on it for.
    closure := ARRAY(
        WITH RECURSIVE emptied(oid) AS (
            SELECT c.oid
              FROM pg_class c
              JOIN pg_namespace ns ON ns.oid = c.relnamespace
             WHERE ns.nspname = 'public' AND c.relkind = 'r'
               AND c.relname IN ('individual', 'encounter', 'program_enrolment', 'program_encounter')
            UNION
            SELECT con.conrelid
              FROM pg_constraint con
              JOIN emptied e ON con.confrelid = e.oid
             WHERE con.contype = 'f'
        )
        SELECT c.relname
          FROM emptied e
          JOIN pg_class c ON c.oid = e.oid
         ORDER BY c.relname);

    IF cardinality(closure) = 0 THEN
        RAISE EXCEPTION 'none of the four transactional tables exist in this schema';
    END IF;

    -- **The guard that matters.** If a future foreign key points at one of the four from a
    -- metadata table, CASCADE reaches it and a reset quietly becomes a re-provisioning. Stopping
    -- is the only safe response: by the time the TRUNCATE has run the rows are gone.
    breached := ARRAY(SELECT t FROM unnest(closure) AS t WHERE t = ANY (survives) ORDER BY t);
    IF cardinality(breached) > 0 THEN
        RAISE EXCEPTION 'TRUNCATE CASCADE would reach %, which this reset must preserve. '
                        'A foreign key has been added since this was written; reload.sql cannot '
                        'restore these, so the reset is refusing rather than emptying them.',
                        array_to_string(breached, ', ');
    END IF;

    RAISE NOTICE 'CASCADE closure (% tables): %', cardinality(closure),
                 array_to_string(closure, ', ');

    -- Of those, the ones that own audit rows.
    carriers := ARRAY(
        SELECT t
          FROM unnest(closure) AS t
         WHERE EXISTS (SELECT 1
                         FROM pg_attribute a
                         JOIN pg_class c ON c.oid = a.attrelid
                         JOIN pg_namespace ns ON ns.oid = c.relnamespace
                        WHERE ns.nspname = 'public' AND c.relname = t
                          AND a.attname = 'audit_id' AND a.attnum > 0 AND NOT a.attisdropped)
         ORDER BY t);

    IF cardinality(carriers) = 0 THEN
        RAISE EXCEPTION 'no table in the cascade closure has an audit_id column, which cannot be '
                        'right -- individual, encounter, program_enrolment and program_encounter '
                        'all carry one. The schema has moved under this script.';
    END IF;

    FOREACH tbl IN ARRAY carriers LOOP
        EXECUTE format('INSERT INTO doomed_audit (id) SELECT audit_id FROM %I '
                       'WHERE audit_id IS NOT NULL', tbl);
        GET DIAGNOSTICS n = ROW_COUNT;
        total := total + n;
        RAISE NOTICE '  captured % audit rows from %', n, tbl;
    END LOOP;
    RAISE NOTICE 'captured % audit rows in total', total;
END
$reset$;

-- The planner has no statistics for a temp table it has just been handed.
ANALYZE doomed_audit;

TRUNCATE individual, encounter, program_enrolment, program_encounter CASCADE;

DELETE FROM audit a USING doomed_audit d WHERE a.id = d.id;

COMMIT;

-- Outside the transaction, and the reason the table reaches a steady size rather than a smaller
-- one: this marks the dead tuples reusable so the next reload fills them instead of extending the
-- file. Not VACUUM FULL -- that takes an ACCESS EXCLUSIVE lock and rewrites the table to reclaim
-- space the next cycle is about to ask for anyway.
VACUUM (ANALYZE) audit;
