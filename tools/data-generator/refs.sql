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
  -- The target's own location hierarchy. Without these the generator falls back to using a
  -- level's depth as its type id, which is only ever right on an empty database: a bundle's
  -- types are numbered wherever they landed, and its hierarchy is whatever the implementation
  -- designed -- not the six-level State/District/Block/PHC/Sub-Centre/Village this tool assumes.
  -- `parent_id` is what says which of them form a chain; `level` alone does not, because a real
  -- establishment hangs alternates like a health centre off the middle of it.
  'address_level_types', (
    select coalesce(json_agg(json_build_object(
      'id', id, 'uuid', uuid, 'name', name, 'level', level,
      'parent_id', parent_id, 'organisation_id', organisation_id
    ) order by level desc), '[]'::json)
    from address_level_type where is_voided = false
  ),
  -- **Where subjects may be registered**, which is not the same as the deepest location type.
  --
  -- `customRegistrationLocations` in organisation_config names, per subject type, the address
  -- level types a subject of that type can be registered at. When it is set, the sync scope query
  -- stops using the user's whole catchment: AddressLevelService calls
  -- getAddressLevelsForCatchmentAndMatchingAddressLevelTypeIds instead, and an empty intersection
  -- is a hard "match nothing" rather than a no-op
  -- (OperatingIndividualScopeAwareRepository: `cb.equal(from.get("id"), cb.literal(0))`).
  --
  -- This is what made org 3's 900 individuals invisible. Tanuh restricts Patient registration to
  -- Village; the generator had placed every subject, and every catchment, one level below at
  -- Health Center. The intersection was empty, so `Individual`, `SubjectMigration`,
  -- `SubjectProgramEligibility` and `IndividualRelationship` were added by
  -- SyncDetailsService.getAllSyncableItems and then dropped again by filterChangedEntities --
  -- exactly the four entities keyed by subjectTypeUuid. `Encounter` is keyed on encounter type,
  -- never applies this filter, and so survived, which is why the dataset looked half-working.
  --
  -- Matching is on `address_id IN (...)` directly, not on lineage, so registering a subject at a
  -- descendant of a permitted type does not count.
  'registration_locations', (
    select coalesce(json_agg(json_build_object(
      'subject_type_uuid', e ->> 'subjectTypeUUID',
      'location_type_uuids', e -> 'locationTypeUUIDs'
    )), '[]'::json)
    -- Cast to jsonb rather than relying on the column's type: `?` and `->` are spelled the same
    -- either way once it is jsonb, and this works whether settings is declared json or jsonb.
    from organisation_config oc,
         lateral jsonb_array_elements(oc.settings::jsonb -> 'customRegistrationLocations') e
    where oc.settings::jsonb ? 'customRegistrationLocations'
      and jsonb_typeof(oc.settings::jsonb -> 'customRegistrationLocations') = 'array'
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
