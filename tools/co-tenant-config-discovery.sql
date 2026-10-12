-- What a bundle import actually creates, discovered rather than assumed.
--
--   psql "$DB" -f tools/co-tenant-config-discovery.sql            -- probe org defaults to 20
--   psql "$DB" -v probe_org=21 -f tools/co-tenant-config-discovery.sql
--
-- Read-only. No table is written, nothing is locked beyond a catalogue read, and the row counts
-- are estimates from pg_class where a scan would be expensive.
--
-- **Why discover instead of listing the tables.** The co-tenant config clone copies what the
-- importer produced into organisations that will never have an import run for them. A table left
-- out of a hand-written list produces no error: those organisations never sync, so nothing reads
-- the config and nothing complains. The same argument reset-transactional.sql makes for reading
-- pg_constraint rather than restating the closure applies here, and more sharply -- there, a
-- missed table shows up as rows that would not delete.
--
-- **The probe organisation is the measurement.** `cotenant-timing-probe` (id 20) was created and
-- had one bundle imported into it and nothing else has ever touched it. So "tables holding rows
-- for organisation 20" is the empirical answer to what an import creates, which is a stronger
-- statement than "tables carrying an organisation_id column" -- many of those are transactional,
-- and some config tables may hold nothing for a given bundle.

\set ON_ERROR_STOP on
\if :{?probe_org}
\else
  \set probe_org 20
\endif

\echo
\echo === 1. tables carrying organisation_id, and what the probe organisation has in each ===
\echo

DROP TABLE IF EXISTS pg_temp._disco_counts;
CREATE TEMP TABLE _disco_counts(table_name text, probe_rows bigint, est_total bigint);

-- **:probe_org cannot be read inside the DO block.** psql substitutes variables while lexing and
-- skips dollar-quoted strings, so `probe int := :probe_org` would be a syntax error at best and
-- the wrong organisation at worst. Carried through a session GUC, which is interpolated here --
-- outside the dollar quotes -- and read back inside.
SELECT set_config('disco.probe_org', :'probe_org', false);

DO $$
DECLARE
  r record;
  n bigint;
  probe int := current_setting('disco.probe_org')::int;
BEGIN
  FOR r IN
    SELECT c.relname
    FROM pg_class c
    JOIN pg_namespace ns ON ns.oid = c.relnamespace
    JOIN pg_attribute a ON a.attrelid = c.oid
    WHERE c.relkind = 'r'
      AND ns.nspname = 'public'
      AND a.attname = 'organisation_id'
      AND NOT a.attisdropped
    ORDER BY c.relname
  LOOP
    EXECUTE format('SELECT count(*) FROM public.%I WHERE organisation_id = $1', r.relname)
      INTO n USING probe;
    INSERT INTO _disco_counts
      SELECT r.relname, n,
             (SELECT c.reltuples::bigint FROM pg_class c
               JOIN pg_namespace ns ON ns.oid = c.relnamespace
              WHERE ns.nspname = 'public' AND c.relname = r.relname);
  END LOOP;
END $$;

-- Ordered so the tables the clone must carry come first.
SELECT table_name,
       probe_rows,
       est_total,
       CASE WHEN probe_rows > 0 THEN 'import creates rows here'
            ELSE 'empty for the probe' END AS verdict
FROM _disco_counts
ORDER BY (probe_rows > 0) DESC, probe_rows DESC, table_name;

\echo
\echo === 2. foreign keys among the tables that the import populated ===
\echo

SELECT child.relname  AS child,
       a.attname     AS child_column,
       parent.relname AS parent,
       con.confdeltype AS on_delete,
       con.conname
FROM pg_constraint con
JOIN pg_class child  ON child.oid  = con.conrelid
JOIN pg_class parent ON parent.oid = con.confrelid
JOIN unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord) ON true
JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum
WHERE con.contype = 'f'
  AND child.relname  IN (SELECT table_name FROM _disco_counts WHERE probe_rows > 0)
ORDER BY parent.relname, child.relname, a.attname;

\echo
\echo === 3. what the clone must regenerate rather than copy ===
\echo
\echo -- uuid columns, and any unique constraint that would collide if a row were copied verbatim.
\echo -- organisation_config carries UNIQUE (uuid, organisation_id), which a straight copy survives;
\echo -- a globally unique uuid is one it does not.
\echo

SELECT c.relname AS table_name,
       con.conname,
       CASE con.contype WHEN 'u' THEN 'unique' WHEN 'p' THEN 'primary key' END AS kind,
       (SELECT string_agg(a.attname, ', ' ORDER BY k.ord)
          FROM unnest(con.conkey) WITH ORDINALITY AS k(attnum, ord)
          JOIN pg_attribute a ON a.attrelid = con.conrelid AND a.attnum = k.attnum) AS columns
FROM pg_constraint con
JOIN pg_class c ON c.oid = con.conrelid
WHERE con.contype IN ('u','p')
  AND c.relname IN (SELECT table_name FROM _disco_counts WHERE probe_rows > 0)
ORDER BY c.relname, con.contype DESC, con.conname;

\echo
\echo === 4. the sequence each table allocates ids from ===
\echo

SELECT table_name,
       pg_get_serial_sequence('public.' || quote_ident(table_name), 'id') AS id_sequence
FROM _disco_counts
WHERE probe_rows > 0
ORDER BY table_name;
