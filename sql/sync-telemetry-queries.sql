-- Queries over sync_telemetry.entity_status / app_info, as written by avni-client from the
-- release that added per-entity phase durations (avniproject/avni-client#2121).
--
-- Each query is standalone: copy one out and run it anywhere that can SELECT. Nothing here
-- creates objects or depends on session state.
--
-- Four things these queries encode, all easy to get wrong:
--
-- 1. Rows are deduplicated on uuid. A telemetry row stays in the client's entity queue until its
--    post succeeds, so a post that reaches the server but is not confirmed by the phone is sent
--    again. sync_telemetry has no unique constraint on uuid and the controller inserts rather
--    than upserting, so both copies persist and any sum over them double counts.
--
-- 2. Phase keys are sparse: written only onto entities that did something. Within a row that
--    reports phases, an absent key means the entity did nothing, and coalescing it to 0 is right.
--
-- 3. Whether a row reports phases at all is a row-level question. A client older than that
--    release writes no phase keys anywhere, and defaulting those to 0 would invent measurements
--    that were never taken. app_info.pageSize is written on every sync from the release onwards,
--    always as a present key even when null, so its presence is the gate.
--
-- 4. NULLIF guards every denominator: an entity can legitimately report 0 pages or 0 rows.
--
-- byType is absent for entities with no subtypes, and is coalesced to '{}' so the lateral join
-- keeps those entities rather than dropping them.
--
-- The 90 day window keeps the scan on sync_telemetry_sync_start_time_idx. It cannot hide a
-- duplicate pair: a re-sent row carries the original sync_start_time, so both copies fall in the
-- same window. Widen or drop it for an all-time figure.


-- 1. Which app versions report phases at all.
with telemetry as (
    select distinct on (uuid) *
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    order by uuid, id desc
)
select app_version,
       bool_or(app_info ? 'pageSize') as reports_phases,
       count(*)                       as syncs
from telemetry
group by app_version
order by app_version;


-- 2. Where pull time goes, per entity.
with telemetry as (
    select distinct on (uuid) *
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    order by uuid, id desc
),
sync_pull as (
    select e->>'entity'                            as entity,
           coalesce((e->>'done')::numeric, 0)      as rows_pulled,
           coalesce((e->>'networkMs')::numeric, 0) as network_ms,
           coalesce((e->>'parseMs')::numeric, 0)   as parse_ms,
           coalesce((e->>'persistMs')::numeric, 0) as persist_ms,
           coalesce((e->>'pages')::numeric, 0)     as pages
    from telemetry st
    -- jsonb_array_elements raises on a non-array; this skips null and malformed entity_status
    cross join lateral jsonb_array_elements(st.entity_status->'pull') e
    where jsonb_typeof(st.entity_status->'pull') = 'array'
      and st.app_info ? 'pageSize'
)
select entity,
       round(sum(network_ms + parse_ms + persist_ms)/1000.0, 1) as total_s,
       round(sum(network_ms)/1000.0, 1)                         as network_s,
       round(sum(parse_ms)/1000.0, 1)                           as parse_s,
       round(sum(persist_ms)/1000.0, 1)                         as persist_s,
       sum(rows_pulled)                                         as rows_pulled,
       sum(pages)                                               as pages,
       round(sum(persist_ms)/nullif(sum(rows_pulled), 0), 2)    as persist_ms_per_row,
       round(sum(network_ms)/nullif(sum(pages), 0), 1)          as network_ms_per_page
from sync_pull
group by entity
order by total_s desc nulls last
limit 15;


-- 3. Per encounter or subject type, for the entities pulled once per type.
-- Program encounters carry an encounter_type uuid; there is no program_encounter_type table.
-- The uuid itself is the fallback name for a type that has since been deleted.
with telemetry as (
    select distinct on (uuid) *
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    order by uuid, id desc
),
pull_types as (
    select e->>'entity' as entity, t.type_uuid, t.type_status
    from telemetry st
    cross join lateral jsonb_array_elements(st.entity_status->'pull') e
    cross join lateral jsonb_each(coalesce(e->'byType', '{}'::jsonb)) t(type_uuid, type_status)
    where jsonb_typeof(st.entity_status->'pull') = 'array'
      and st.app_info ? 'pageSize'
)
select p.entity,
       coalesce(et.name, sbt.name, p.type_uuid)                            as type_name,
       round(sum((p.type_status->>'persistMs')::numeric)/1000.0, 1)        as persist_s,
       round(sum((p.type_status->>'networkMs')::numeric)/1000.0, 1)        as network_s,
       sum((p.type_status->>'done')::numeric)                              as rows_pulled,
       round(sum((p.type_status->>'persistMs')::numeric)
             / nullif(sum((p.type_status->>'done')::numeric), 0), 2)       as persist_ms_per_row
from pull_types p
left join encounter_type et on et.uuid = p.type_uuid
left join subject_type  sbt on sbt.uuid = p.type_uuid
group by 1, 2
order by persist_s desc nulls last
limit 15;


-- 4. Push, and the queue read that happens before any post.
-- readMs is the queue read plus toResource conversion of every queued record. It runs once per
-- entity type before any post, so it has no per-post count to divide by.
with telemetry as (
    select distinct on (uuid) *
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    order by uuid, id desc
),
sync_push as (
    select e->>'entity'                              as entity,
           coalesce((e->>'readMs')::numeric, 0)      as read_ms,
           coalesce((e->>'serializeMs')::numeric, 0) as serialize_ms,
           coalesce((e->>'networkMs')::numeric, 0)   as network_ms,
           coalesce((e->>'persistMs')::numeric, 0)   as persist_ms,
           coalesce((e->>'posts')::numeric, 0)       as posts
    from telemetry st
    cross join lateral jsonb_array_elements(st.entity_status->'push') e
    where jsonb_typeof(st.entity_status->'push') = 'array'
      and st.app_info ? 'pageSize'
)
select entity,
       round(sum(read_ms)/1000.0, 1)                     as read_s,
       round(sum(serialize_ms)/1000.0, 1)                as serialize_s,
       round(sum(network_ms)/1000.0, 1)                  as network_s,
       round(sum(persist_ms)/1000.0, 1)                  as persist_s,
       sum(posts)                                        as posts,
       round(sum(network_ms)/nullif(sum(posts), 0), 1)   as network_ms_per_post
from sync_push
group by entity
order by network_s desc nulls last
limit 10;


-- 5. Page size split across the fleet.
with telemetry as (
    select distinct on (uuid) *
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    order by uuid, id desc
)
select coalesce(app_info->>'pageSize', 'not reported') as page_size,
       count(*)                                        as syncs
from telemetry
group by 1
order by 2 desc;


-- 6. How much duplication the dedupe above is actually absorbing.
-- Deliberately not deduplicated. excess_rows is what distinct on (uuid) removes, and so how far
-- an undeduplicated sum would overstate. If this is run often, an index on (uuid) turns the
-- aggregate into an index-only scan; there is none today.
select count(*)                as uuids_with_duplicates,
       sum(copies)             as rows_involved,
       sum(copies) - count(*)  as excess_rows,
       max(copies)             as worst_uuid
from (
    select uuid, count(*) as copies
    from sync_telemetry
    where sync_start_time > now() - interval '90 days'
    group by uuid
    having count(*) > 1
) d;
