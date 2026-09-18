-- The metadata ids the generator needs from the target, as JSON.
--
--   psql -d <target_db> -At -f refs.sql > refs.json
--
-- Run after the implementation bundle has been loaded, since these are its rows.
--
-- The sync concepts are gated on their _usable flag, because that is what the server does:
-- OperatingIndividualScopeAwareRepository checks isSyncRegistrationConcept1Usable before it will
-- filter on the column. Reporting a concept the flag disables would make the generator write a
-- sync_concept value no query ever reads.
select json_build_object(
  'subject_types', (
    select coalesce(json_agg(json_build_object(
      'id', id, 'uuid', uuid, 'name', name,
      'organisation_id', organisation_id,
      'sync_concept_1', case when coalesce(sync_registration_concept_1_usable, false)
                             then sync_registration_concept_1 end,
      'sync_concept_2', case when coalesce(sync_registration_concept_2_usable, false)
                             then sync_registration_concept_2 end
    ) order by id), '[]'::json)
    from subject_type where is_voided = false
  ),
  'programs', (
    select coalesce(json_agg(json_build_object(
      'id', id, 'uuid', uuid, 'name', name, 'organisation_id', organisation_id
    ) order by id), '[]'::json)
    from program where is_voided = false
  ),
  'encounter_types', (
    select coalesce(json_agg(json_build_object(
      'id', id, 'uuid', uuid, 'name', name, 'organisation_id', organisation_id
    ) order by id), '[]'::json)
    from encounter_type where is_voided = false
  ),
  'audit_user_id', (
    select min(id) from users where is_voided = false
  )
);
