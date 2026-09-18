-- H5 statistical gate: the statistics a generated dataset has to be judged on.
--
-- Run against the GENERATED database after loading and ANALYZE. Feed the output to
-- validate.py, which compares it against profiles/production-2026-09.json.
--
--   psql -d <generated_db> -A -F',' -f validate.sql
--
-- Index size is the point of this file. Row counts the generator sets directly, so matching them
-- proves only that the loader worked. Index bytes per row it cannot target -- that falls out of
-- how many distinct observation keys each row actually carries -- so it is the one figure that
-- says whether the data is shaped like production rather than merely sized like it.

\echo === rows, table and index size per table ===
select c.relname                                   as table,
       c.reltuples::bigint                          as rows,
       pg_table_size(c.oid)                         as table_bytes,
       pg_indexes_size(c.oid)                       as all_index_bytes
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
order by c.relname;

\echo
\echo === GIN observation indexes, the check that cannot be faked ===
-- A generated index an order of magnitude lighter per row than production's means the observation
-- cardinality is wrong: the index is cache-resident, and every push figure comes out optimistic.
select i.relname                                    as table,
       x.indexrelname                                as index,
       pg_relation_size(x.indexrelid)                as gin_observation_bytes,
       i.reltuples::bigint                           as rows,
       round(pg_relation_size(x.indexrelid) / nullif(i.reltuples, 0))::bigint as bytes_per_row
from pg_stat_user_indexes x
join pg_class i on i.relname = x.relname and i.relnamespace = 'public'::regnamespace
where x.schemaname = 'public'
  and x.indexrelname like '%obs_idx'
  and x.relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
order by x.relname;

\echo
\echo === observation shape, to compare against Q6 ===
-- Sampled at 1%, as Q6 was, so the two are measured the same way.
select 'program_encounter' as table, * from (
  select percentile_cont(0.5)  within group (order by k)::int as obs_keys_p50,
         percentile_cont(0.95) within group (order by k)::int as obs_keys_p95,
         avg(sz)::int                                          as obs_mean_bytes
  from (select (select count(*) from jsonb_object_keys(observations)) as k,
               pg_column_size(observations) as sz
        from program_encounter tablesample system (1) where observations is not null) t) s
union all
select 'individual', * from (
  select percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int, avg(sz)::int
  from (select (select count(*) from jsonb_object_keys(observations)) as k,
               pg_column_size(observations) as sz
        from individual tablesample system (1) where observations is not null) t) s
union all
select 'encounter', * from (
  select percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int, avg(sz)::int
  from (select (select count(*) from jsonb_object_keys(observations)) as k,
               pg_column_size(observations) as sz
        from encounter tablesample system (1) where observations is not null) t) s
union all
select 'program_enrolment', * from (
  select percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int, avg(sz)::int
  from (select (select count(*) from jsonb_object_keys(observations)) as k,
               pg_column_size(observations) as sz
        from program_enrolment tablesample system (1) where observations is not null) t) s;

\echo
\echo === distinct concepts per organisation ===
-- Compare against the bundle's own reachable concept set, NOT against Q6's platform-wide 5,623.
-- That figure spans 986 organisations; one bundle reaches a few hundred.
select organisation_id,
       count(distinct key) as distinct_concepts
from (select organisation_id, jsonb_object_keys(observations) as key
      from program_encounter tablesample system (1)) t
group by 1 order by 1;

\echo
\echo === timestamp spread, to compare against Q14 ===
select 'program_encounter' as table,
       percentile_cont(array[0.5, 0.9, 0.99]) within group (
         order by extract(epoch from (now() - last_modified_date_time)) / 86400
       ) as age_days_p50_p90_p99,
       round(100.0 * count(*) filter (
         where last_modified_date_time > created_date_time + interval '1 hour'
       ) / nullif(count(*), 0), 2) as pct_edited_after_creation
from program_encounter tablesample system (1);

\echo
\echo === sanity: nothing the sync path needs is null ===
-- A null here loads without complaint and quietly keeps the data off the index paths production
-- uses, which is the failure mode that produces optimistic numbers rather than an error.
select 'individual' as table,
       count(*) filter (where address_id is null)          as null_address_id,
       count(*) filter (where observations is null)        as null_observations,
       count(*) filter (where last_modified_date_time is null) as null_last_modified
from individual
union all
select 'program_encounter',
       count(*) filter (where address_id is null),
       count(*) filter (where observations is null),
       count(*) filter (where last_modified_date_time is null)
from program_encounter;
