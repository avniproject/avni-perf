-- Is this environment's index set production's, and does the sync path use it?
--
--   psql -d <db> -f tools/index-parity-check.sql
--
-- **Why two questions rather than one number.** H5 compares total index bytes per row, which
-- conflates three things: whether the indexes exist, how bloated they are, and how wide the rows
-- are. That is why it could not tell "five indexes missing" from "indexes are smaller" -- the
-- first reading was right on 30 Sep, and after db-bootstrap added production's `sync_N` family
-- the figure only moved from 0.16x to 0.33x on `encounter`. The residue needs a different
-- instrument.
--
-- Section 1 answers set completeness by name, which bytes cannot. Section 2 answers the question
-- underneath all of it: does a catchment-scoped sync use the `address_id` index, or scan?
--
-- **What to expect if the remaining gap is bloat rather than absence.** Indexes here were built
-- by CREATE INDEX over loaded data, so they pack near 90% fillfactor with no dead entries.
-- Production's grew through years of inserts: page splits settle a b-tree around 70% full and
-- dead entries persist until a REINDEX these tables rarely get. 1.3x from fill alone, and 2-3x
-- overall is unremarkable -- which is the size of what is left.

\pset pager off

\echo '=== 1. the index set, by name ==='
\echo '--- compare against production. A name here that production lacks is as interesting as'
\echo '--- one it has and this does not: both mean the plans can differ.'
select i.tablename,
       i.indexname,
       am.amname                                        as method,
       pg_size_pretty(pg_relation_size(c.oid))          as size,
       round(pg_relation_size(c.oid)::numeric
             / nullif(s.n_live_tup, 0), 0)              as bytes_per_row,
       s.idx_scan                                       as scans
  from pg_indexes i
  join pg_class c   on c.relname = i.indexname
  join pg_am am     on am.oid = c.relam
  left join pg_stat_user_indexes x on x.indexrelname = i.indexname
  left join pg_stat_user_tables  s on s.relname = i.tablename
 where i.schemaname = 'public'
   and i.tablename in ('individual', 'encounter', 'program_enrolment', 'program_encounter')
 order by i.tablename, pg_relation_size(c.oid) desc;

\echo ''
\echo '=== 2. does a catchment-scoped sync use the address_id index? ==='
\echo '--- This is the predicate every location-scoped pull runs:'
\echo '---   OperatingIndividualScopeAwareRepository filters lastModifiedDateTime between,'
\echo '---   addressLevel.id IN (...), ordered by lastModifiedDateTime, id.'
\echo '--- A Seq Scan over 1.8M rows here means the pull path is not indexed and every'
\echo '--- scenario measures the wrong thing. An Index Scan means the byte gap is cosmetic'
\echo '--- for a sync test, the same conclusion the observation GIN already reached.'
\echo ''
\echo '--- encounter, organisation 10, its three village addresses ---'
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)
select *
  from encounter
 where organisation_id = 10
   and address_id in (201000046, 201000047, 201000048)
   and last_modified_date_time between timestamptz '1900-01-01' and now()
 order by last_modified_date_time, id
 limit 100;

\echo ''
\echo '--- individual, same scope ---'
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)
select *
  from individual
 where organisation_id = 10
   and address_id in (201000046, 201000047, 201000048)
   and last_modified_date_time between timestamptz '1900-01-01' and now()
 order by last_modified_date_time, id
 limit 100;

\echo ''
\echo '--- and one real catchment, which is what a field worker actually pulls ---'
\echo '--- (the server expands a catchment to its descendants; this is the expanded set) ---'
EXPLAIN (ANALYZE, BUFFERS, COSTS OFF, TIMING OFF)
select *
  from encounter
 where organisation_id = 10
   and address_id in (select addresslevel_id
                        from catchment_address_mapping m
                        join catchment c on c.id = m.catchment_id
                       where c.uuid = 'catchment-10-201000001')
   and last_modified_date_time between timestamptz '1900-01-01' and now()
 order by last_modified_date_time, id
 limit 100;
