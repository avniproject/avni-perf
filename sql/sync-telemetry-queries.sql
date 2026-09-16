-- Queries over sync_telemetry.entity_status / app_info, as written by avni-client from the
-- release that added per-entity phase durations (avniproject/avni-client#2121).
--
-- Phase keys are sparse: they are written only onto entities that actually did something during
-- a sync. Within a row that reports phases, an absent key means the entity did nothing, and
-- coalescing it to 0 is exactly right.
--
-- What a per-entity key cannot tell you is whether the row reports phases at all -- a client
-- older than that release writes no phase keys anywhere, and defaulting those to 0 would invent
-- measurements that were never taken and drag every average down. That question is settled at
-- the row instead: app_info.pageSize is written on every sync from the release onwards, and is
-- always a present key even when the value is null, so its presence is the gate.
--
-- byType is absent for entities that have no subtypes, and is coalesced to '{}' so the lateral
-- join keeps those entities instead of dropping them.
--
-- NULLIF guards every denominator: an entity can legitimately report 0 pages or 0 rows.

\echo === 1. base view: one row per (sync, pulled entity) ===
create or replace temp view sync_pull as
select st.id as sync_id, st.app_version, st.sync_start_time, st.sync_status,
       st.app_info ? 'pageSize'                as reports_phases,
       e->>'entity'                            as entity,
       coalesce((e->>'todo')::numeric, 0)      as rows_expected,
       coalesce((e->>'done')::numeric, 0)      as rows_pulled,
       coalesce((e->>'networkMs')::numeric, 0) as network_ms,
       coalesce((e->>'parseMs')::numeric, 0)   as parse_ms,
       coalesce((e->>'persistMs')::numeric, 0) as persist_ms,
       coalesce((e->>'pages')::numeric, 0)     as pages,
       e->'byType'                             as by_type
from sync_telemetry st
-- jsonb_array_elements raises on a non-array; this skips null and malformed entity_status
cross join lateral jsonb_array_elements(st.entity_status->'pull') e
where jsonb_typeof(st.entity_status->'pull') = 'array';

\echo === 2. which app versions report phases at all ===
select app_version, bool_or(reports_phases) as reports_phases, count(distinct sync_id) as syncs
from sync_pull group by app_version order by app_version;

\echo === 3. where pull time goes, per entity ===
select entity,
       round(sum(network_ms + parse_ms + persist_ms)/1000.0, 1) as total_s,
       round(sum(network_ms)/1000.0, 1)                         as network_s,
       round(sum(parse_ms)/1000.0, 1)                           as parse_s,
       round(sum(persist_ms)/1000.0, 1)                         as persist_s,
       sum(rows_pulled)                                         as rows_pulled,
       sum(pages)                                               as pages,
       round(sum(persist_ms)/nullif(sum(rows_pulled), 0), 2)    as persist_ms_per_row,
       round(sum(network_ms)/nullif(sum(pages), 0), 0)          as network_ms_per_page
from sync_pull
where reports_phases
group by entity
order by total_s desc nulls last
limit 15;

\echo === 4. per encounter/subject type ===
-- Program encounters carry an encounter_type uuid; there is no program_encounter_type table.
-- The uuid itself is the fallback name for a type that has since been deleted.
select sp.entity,
       coalesce(et.name, sbt.name, t.type_uuid)                  as type_name,
       round(sum((tv->>'persistMs')::numeric)/1000.0, 1)         as persist_s,
       round(sum((tv->>'networkMs')::numeric)/1000.0, 1)         as network_s,
       sum((tv->>'done')::numeric)                               as rows_pulled,
       round(sum((tv->>'persistMs')::numeric)
             / nullif(sum((tv->>'done')::numeric), 0), 2)        as persist_ms_per_row
from sync_pull sp
cross join lateral jsonb_each(coalesce(sp.by_type, '{}'::jsonb)) t(type_uuid, tv)
left join encounter_type et on et.uuid = t.type_uuid
left join subject_type  sbt on sbt.uuid = t.type_uuid
where sp.reports_phases
group by 1, 2
order by persist_s desc nulls last
limit 15;

\echo === 5. push, and the read cost that happens before any post ===
-- readMs is the queue read plus toResource conversion of every queued record. It runs once per
-- entity type before any post, so it has no per-post count to divide by.
select e->>'entity' as entity,
       round(sum(coalesce((e->>'readMs')::numeric, 0))/1000.0, 1)      as read_s,
       round(sum(coalesce((e->>'serializeMs')::numeric, 0))/1000.0, 1) as serialize_s,
       round(sum(coalesce((e->>'networkMs')::numeric, 0))/1000.0, 1)   as network_s,
       round(sum(coalesce((e->>'persistMs')::numeric, 0))/1000.0, 1)   as persist_s,
       sum(coalesce((e->>'posts')::numeric, 0))                        as posts,
       round(sum(coalesce((e->>'networkMs')::numeric, 0))
             / nullif(sum(coalesce((e->>'posts')::numeric, 0)), 0), 0) as network_ms_per_post
from sync_telemetry st
cross join lateral jsonb_array_elements(st.entity_status->'push') e
where jsonb_typeof(st.entity_status->'push') = 'array'
  and st.app_info ? 'pageSize'
group by 1
order by network_s desc nulls last
limit 10;

\echo === 6. page size split across the fleet ===
select coalesce(app_info->>'pageSize', 'not reported') as page_size, count(*) as syncs
from sync_telemetry group by 1 order by 2 desc;
