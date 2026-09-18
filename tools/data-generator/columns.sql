-- The target's own column lists, as JSON, for the generator to project rows onto.
--
--   psql -d <target_db> -At -f columns.sql > columns.json
--
-- Read from the database rather than hardcoded, because 484 Flyway migrations have already moved
-- this schema and a stale list produces a COPY that either fails or -- far worse -- shifts every
-- value one column to the left and loads silently.
--
-- Generated columns are excluded: COPY cannot write them. Identity and defaulted columns are
-- included, because the generator assigns its own ids to wire foreign keys without round-tripping.
select json_object_agg(table_name, columns)
from (
  select table_name,
         json_agg(column_name order by ordinal_position) as columns
  from information_schema.columns
  where table_schema = 'public'
    and table_name in ('address_level', 'catchment', 'catchment_address_mapping', 'users',
                       'individual', 'program_enrolment', 'program_encounter', 'encounter')
    and is_generated = 'NEVER'
  group by table_name
) t;
