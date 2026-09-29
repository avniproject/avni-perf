-- The target's own column shapes, as JSON, for the generator to project rows onto and to check
-- itself against.
--
--   psql -d <target_db> -At -f columns.sql > columns.json
--
-- Read from the database rather than hardcoded, because 484 Flyway migrations have already moved
-- this schema and a stale list produces a COPY that either fails or -- far worse -- shifts every
-- value one column to the left and loads silently.
--
-- **It carries nullability, type and default, not just names.** The name-only version could only
-- catch a column that does not exist. It could not catch any of these, each found on a real
-- database after passing every offline test:
--
--   * `users.version` was dropped from that table alone, so writing it fails the insert
--   * `users.name` and `operating_individual_scope` are NOT NULL with no default, so omitting
--     them fails the insert
--   * every structural table's timestamps feed a BEFORE INSERT trigger into `audit`, whose date
--     columns are NOT NULL, so a null fails with a message naming a table you never wrote to
--   * `id` is `SERIAL`, meaning int4, while the Java entity says `Long` -- so a tenant id scheme
--     reaching 51 billion fails at load with "integer out of range"
--
-- A Java entity cannot tell you a column's width, its nullability after 484 migrations, or
-- whether a trigger reads it. This can.
--
-- Generated columns are excluded: COPY cannot write them. Identity and defaulted columns are
-- included, because the generator assigns its own ids to wire foreign keys without round-tripping.
select json_object_agg(table_name, cols)
from (
  select table_name,
         json_agg(json_build_object(
           'name', column_name,
           'type', data_type,
           'required', (is_nullable = 'NO' and column_default is null),
           'nullable', (is_nullable = 'YES'),
           'default', column_default
         ) order by ordinal_position) as cols
  from information_schema.columns
  where table_schema = 'public'
    and table_name in ('address_level', 'address_level_type', 'catchment',
                       'catchment_address_mapping', 'users', 'groups', 'user_group',
                       'individual', 'program_enrolment', 'program_encounter', 'encounter')
    and is_generated = 'NEVER'
  group by table_name
) t;
