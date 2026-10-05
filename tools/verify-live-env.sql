-- Does the LIVE environment still match the context archived beside a run?
--
--   psql -d <db> -f tools/verify-live-env.sql
--
-- Read-only. Deliberately narrow: this covers only the two questions no other
-- tool in here answers. For the rest, use what already exists --
--   tools/index-parity-check.sql          the index set by name, with sizes,
--                                         scan counts and the sync-path plans
--   tools/data-generator/validate_stats.sql   row counts, index bytes and the
--                                         observation shape -> stats.json
--
-- **Why this exists.** run-scenario.sh copies parity-report.md, pg_settings.csv
-- and stats.json out of /opt/avni-perf/context into every run directory. That
-- directory is staged by hand, so the archived files are only as current as the
-- last time somebody staged them: ten runs on 5 Oct 2026 carried byte-identical
-- context because it was staged once, not because anything re-checked it. On
-- that occasion it turned out to be accurate -- stats.json matched the live
-- database to the row -- but that was luck confirmed after the fact, which is
-- the argument for confirming it on purpose before the next campaign.

\pset pager off

\echo '=== 1. are the static parameters actually in effect? ==='
\echo '--- pending_restart = t means the value below is NOT what the engine is running.'
\echo '--- A stop/start is not obviously a reboot for this purpose (provision/RESIZE.md'
\echo '--- trap 4, untested), so this is worth reading after any restart.'
select name,
       setting,
       unit,
       source,
       pending_restart
  from pg_settings
 where name in ('max_connections', 'shared_preload_libraries', 'statement_timeout',
                'idle_in_transaction_session_timeout', 'log_min_duration_statement',
                'shared_buffers', 'effective_cache_size', 'autovacuum')
 order by name;

\echo ''
\echo '=== 2. row counts BY ORGANISATION ==='
\echo '--- stats.json is database-wide, so it cannot say how much of the volume belongs'
\echo '--- to the org under test and how much is other datasets sharing the tables. Both'
\echo '--- matter, differently: the org row is what a sync pulls, the total is the table'
\echo '--- and index the planner works through. On 5 Oct 2026 the totals were 1,002,900'
\echo '--- individuals and 3,610,652 encounters across orgs 3, 10 and 11.'
with c as (
            select organisation_id, 'individual'        as tbl, count(*) as n from individual        group by 1
  union all select organisation_id, 'encounter'               , count(*)      from encounter         group by 1
  union all select organisation_id, 'program_enrolment'       , count(*)      from program_enrolment group by 1
  union all select organisation_id, 'program_encounter'       , count(*)      from program_encounter group by 1
)
-- No join to `organisation` for a name: the id is what stats.json, the dataset
-- recipes and teardown_org.py all key on, and under ON_ERROR_STOP=1 one wrong
-- column name would discard the rest of this file.
select organisation_id,
       sum(n) filter (where tbl = 'individual')        as individuals,
       sum(n) filter (where tbl = 'encounter')         as encounters,
       sum(n) filter (where tbl = 'program_enrolment') as enrolments,
       sum(n) filter (where tbl = 'program_encounter') as prog_encounters
  from c
 group by 1
 order by 1;
