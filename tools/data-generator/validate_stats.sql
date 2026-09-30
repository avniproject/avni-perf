-- H5's gate, as JSON. The input `validate.py` actually reads.
--
--   psql -d <generated_db> -At -f validate_stats.sql > stats.json
--   make validate_dataset STATS=stats.json
--
-- Run after loading and after ANALYZE.
--
-- **Why this is separate from validate.sql.** That file prints a report for a person to read,
-- in `\echo`-separated sections. `validate.py` wants `{"table": {"rows": ..., ...}}`, and nothing
-- bridged the two -- the gate could not be run as documented. The statistics here are the same
-- ones, with the same definitions; only the output differs.
--
-- Two deliberate differences from validate.sql, both about small datasets:
--
-- 1. **Row counts are exact**, not `reltuples`. The row check runs at a 0.1% tolerance against
--    what the generator produced, and `reltuples` is an estimate that ANALYZE updates lazily --
--    close enough to read, not close enough to gate on.
--
-- 2. **The observation sample adapts.** validate.sql takes `tablesample system (1)` to match how
--    Q6 measured production. One percent of a 900-row table is nine rows picked by page, which is
--    noise rather than a measurement, so below the threshold every row is read instead. Sampling
--    exists because production is 70 GB; where that does not apply, measuring properly can only
--    make the comparison better.
\set ON_ERROR_STOP on
\set sample_above 500000

with counts as (
  select 'individual'::text as t, count(*)::bigint as rows from individual
  union all select 'program_enrolment', count(*) from program_enrolment
  union all select 'program_encounter', count(*) from program_encounter
  union all select 'encounter',         count(*) from encounter
),
sizes as (
  select c.relname::text as t, pg_indexes_size(c.oid)::bigint as all_index_bytes
  from pg_class c
  join pg_namespace n on n.oid = c.relnamespace
  where n.nspname = 'public'
    and c.relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
),
-- Summed rather than taken singly: a table may carry more than one observation index, and the
-- figure the profile is judged against is the observation indexing as a whole.
--
-- **Matched on what the index is, not on what it is called.** Avni's naming convention changed:
-- `idx_individual_obs` came in with V1_03 and every other observation GIN index arrived in
-- V1_227.4 under the opposite spelling, `<table>_obs_idx`. A `like '%obs_idx'` filter therefore
-- misses exactly one table -- `individual` -- and reports null where a 176 kB index really exists.
-- That is worse than a wrong number: G4 exists to catch index drift, and a null here would let a
-- genuinely absent observation index look identical to a naming mismatch, while never confirming
-- the one that is present.
--
-- `cancel_observations` still matches, which is deliberate: the previous filter caught
-- `encounter_cancel_obs_idx` too, and the profile's figure was measured with it included.
gin as (
  select x.relname::text as t, sum(pg_relation_size(x.indexrelid))::bigint as gin_observation_bytes
  from pg_stat_user_indexes x
  join pg_class ic on ic.oid = x.indexrelid
  join pg_am am on am.oid = ic.relam
  where x.schemaname = 'public'
    and am.amname = 'gin'
    and pg_get_indexdef(x.indexrelid) like '%observations%'
    and x.relname in ('individual', 'program_enrolment', 'program_encounter', 'encounter')
  group by x.relname
),
obs as (
  select 'individual'::text as t,
         percentile_cont(0.5)  within group (order by k)::int as obs_keys_p50,
         percentile_cont(0.95) within group (order by k)::int as obs_keys_p95,
         avg(sz)::int                                         as obs_mean_bytes,
         count(*)::bigint                                     as obs_sampled
  from (select (select count(*) from jsonb_object_keys(x.observations)) as k,
               pg_column_size(x.observations) as sz
        from individual x
        where x.observations is not null
          and (random() < 0.01
               or (select reltuples from pg_class
                    where oid = 'individual'::regclass) < :sample_above)) s
  union all
  select 'program_enrolment',
         percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int,
         avg(sz)::int, count(*)::bigint
  from (select (select count(*) from jsonb_object_keys(x.observations)) as k,
               pg_column_size(x.observations) as sz
        from program_enrolment x
        where x.observations is not null
          and (random() < 0.01
               or (select reltuples from pg_class
                    where oid = 'program_enrolment'::regclass) < :sample_above)) s
  union all
  select 'program_encounter',
         percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int,
         avg(sz)::int, count(*)::bigint
  from (select (select count(*) from jsonb_object_keys(x.observations)) as k,
               pg_column_size(x.observations) as sz
        from program_encounter x
        where x.observations is not null
          and (random() < 0.01
               or (select reltuples from pg_class
                    where oid = 'program_encounter'::regclass) < :sample_above)) s
  union all
  select 'encounter',
         percentile_cont(0.5)  within group (order by k)::int,
         percentile_cont(0.95) within group (order by k)::int,
         avg(sz)::int, count(*)::bigint
  from (select (select count(*) from jsonb_object_keys(x.observations)) as k,
               pg_column_size(x.observations) as sz
        from encounter x
        where x.observations is not null
          and (random() < 0.01
               or (select reltuples from pg_class
                    where oid = 'encounter'::regclass) < :sample_above)) s
)
-- `obs_sampled` is carried so a null percentile can be told apart from a table with no rows:
-- validate.py reports a missing statistic as unmeasured, and an empty sample is a different
-- problem from an empty table.
select json_object_agg(c.t, json_build_object(
         'rows',                  c.rows,
         'all_index_bytes',       s.all_index_bytes,
         'gin_observation_bytes', g.gin_observation_bytes,
         'obs_keys_p50',          o.obs_keys_p50,
         'obs_keys_p95',          o.obs_keys_p95,
         'obs_mean_bytes',        o.obs_mean_bytes,
         'obs_sampled',           o.obs_sampled
       ) order by c.t)
from counts c
left join sizes s on s.t = c.t
left join gin   g on g.t = c.t
left join obs   o on o.t = c.t;
