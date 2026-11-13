-- Execution-plan row 39: one district-level user on pilot-day-180's state-1 (organisation 10).
--
-- District 1 (address_level 201000002) holds 34 villages: 102,000 individuals and 366,452
-- encounters, counted offline from the dataset archive (13 Nov 2026). Avni expands a catchment
-- through each address's lineage (virtual_catchment_address_mapping_table), so one mapping to the
-- district covers every village under it: ~367 pages of 1,000 encounters, past the review's page 100.
--
-- Shaped exactly like a generated field worker (users.tsv / user_group.tsv): the one "Everyone"
-- group (group-10, all privileges), ByCatchment scope, created by user 1. Ids come from the tables'
-- sequences, which load.sql raises past the dataset.
--
-- **The uuids are generator-shaped on purpose.** teardown_org.py removes structural rows by
-- provenance -- catchment 'catchment-10-%', users 'user-10-%', user_group 'usergroup-10-%', and the
-- mappings through their catchment. Rows with any other uuid survive a teardown, and a surviving
-- mapping to District 1 would block that district's own deletion on the next reload. With these
-- uuids the next swap-dataset.sh removes the user along with the dataset.
--
-- Re-runnable: each insert is skipped when its uuid already exists. Refuses unless the dataset rows
-- it depends on are present.

\set ON_ERROR_STOP on
begin;
do $$
declare
  v_group int; v_catchment int; v_user int;
begin
  select id into v_group from groups where uuid = 'group-10' and organisation_id = 10;
  if v_group is null then raise exception 'group-10 not found: is pilot-day-180 loaded?'; end if;
  perform 1 from address_level
    where id = 201000002 and uuid = 'loc-10-201000002' and title = 'District 1' and organisation_id = 10;
  if not found then raise exception 'District 1 (address_level 201000002) not found'; end if;

  select id into v_catchment from catchment where uuid = 'catchment-10-row39-district-1';
  if v_catchment is null then
    insert into catchment (name, uuid, version, organisation_id, is_voided, created_by_id,
                           last_modified_by_id, created_date_time, last_modified_date_time)
    values ('Row 39 District 1 catchment', 'catchment-10-row39-district-1', 0, 10, false, 1, 1,
            '2020-01-01 00:00:00', '2020-01-01 00:00:00')
    returning id into v_catchment;
    insert into catchment_address_mapping (catchment_id, addresslevel_id) values (v_catchment, 201000002);
  end if;

  select id into v_user from users where uuid = 'user-10-row39-district-1';
  if v_user is null then
    insert into users (uuid, username, organisation_id, created_by_id, last_modified_by_id,
                       created_date_time, last_modified_date_time, is_voided, catchment_id,
                       operating_individual_scope, disabled_in_cognito, name)
    values ('user-10-row39-district-1', 'row39-district1@org10', 10, 1, 1,
            '2020-01-01 00:00:00', '2020-01-01 00:00:00', false, v_catchment,
            'ByCatchment', false, 'row39-district1@org10')
    returning id into v_user;
  end if;

  perform 1 from user_group where uuid = 'usergroup-10-row39-district-1';
  if not found then
    insert into user_group (uuid, user_id, group_id, is_voided, version, organisation_id,
                            created_by_id, last_modified_by_id, created_date_time, last_modified_date_time)
    values ('usergroup-10-row39-district-1', v_user, v_group, false, 0, 10, 1, 1,
            '2020-01-01 00:00:00', '2020-01-01 00:00:00');
  end if;
end $$;
commit;

-- What was written, and what the catchment reaches.
select u.username, c.name as catchment, count(distinct v.addresslevel_id) as addresses_in_scope
from users u
join catchment c on c.id = u.catchment_id
join virtual_catchment_address_mapping_table v on v.catchment_id = c.id
where u.uuid = 'user-10-row39-district-1'
group by 1, 2;
