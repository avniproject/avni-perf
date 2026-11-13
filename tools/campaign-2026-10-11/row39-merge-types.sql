-- Execution-plan row 39: make one record type deep enough for the deep-page test.
--
-- The district user (row39-user.sql) reaches 366,452 encounters, but they are spread almost evenly over
-- 12 encounter types (~30,500 each, ~31 pages) -- short of the review's page 100. The harness has no
-- way to sync one type alone, so the depth has to come from the data: this re-types District 1's
-- Personal Examination (34), High Risk Follow-up (47) and Breast Cancer Detection (33) encounters as
-- Mental Health (39), making that one stream 30,816 + 30,775 + 30,752 + 30,621 = 122,964 records,
-- ~123 pages. All twelve types are organisation 10's, for its one subject type (Patient), so the
-- re-typed rows stay valid for the user's sync; their observations are left as they are.
--
-- **Scope**: organisation 10, District 1 (address_level 201000002) and the villages under it, those
-- three types only. Counts checked offline from the dataset archive on 13 Nov 2026; the update refuses
-- unless it touches exactly 92,148 rows. last_modified_date_time is left alone, so nothing else's sync
-- window moves. The audit trigger records the change.
--
-- **The next reload undoes it**: swap-dataset.sh tears organisation 10's encounters down and loads the
-- archive again. The chain reloads before anchor B, so no anchor runs on the re-typed bed.

\set ON_ERROR_STOP on
begin;
do $$
declare n int;
begin
  perform 1 from encounter_type where id = 39 and organisation_id = 10 and uuid = '8e603962-980c-420c-8261-bbf5ed039612';
  if not found then raise exception 'encounter type 39 (Mental Health, organisation 10) not found'; end if;
  update encounter set encounter_type_id = 39
   where organisation_id = 10
     and encounter_type_id in (34, 47, 33)
     and address_id in (select id from address_level
                         where organisation_id = 10
                           and (lineage::text = '201000001.201000002' or lineage::text like '201000001.201000002.%'));
  get diagnostics n = row_count;
  if n <> 92148 then raise exception 'expected to re-type 92,148 encounters, would re-type % -- rolled back', n; end if;
  raise notice 're-typed % encounters to Mental Health (39)', n;
end $$;
commit;

-- The stream the district user will page through.
select count(*) as mental_health_in_district_1
from encounter
where organisation_id = 10 and encounter_type_id = 39
  and address_id in (select id from address_level where organisation_id = 10
                      and (lineage::text = '201000001.201000002' or lineage::text like '201000001.201000002.%'));
