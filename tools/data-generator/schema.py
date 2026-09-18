"""Keep the generator honest about a schema that moves underneath it.

Flyway migrations add columns continuously -- 484 of them at the time of writing. Three of the four
ways that can break a bulk load already fail loudly:

  * a column is **renamed or removed** -- `copy_writer.project` refuses a row key that is not a
    column;
  * a column is **added NOT NULL with no default** -- the `COPY` itself fails;
  * a column's **type changes incompatibly** -- the `COPY` fails on the first bad value.

The fourth is silent, and it is the one that matters. **A new nullable column the generator ought to
populate simply arrives empty.** That is exactly what `sync_concept_1_value` was: added by V1_208 to
carry attribute-based sync, indexed by `sync_3` and `sync_4`, and a generator predating it would have
loaded cleanly while producing data that never touched those index paths. The numbers would have come
out optimistic with nothing to show why.

So every column in the target has to be **accounted for** -- either written, or declared unwritten
with a reason. An unrecognised column is a refusal, not a NULL. That turns each migration into a
one-line decision taken once, instead of a silent gap nobody is looking for.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Highest Flyway migration this contract was checked against. Bump it when the contract is
# reviewed, so drift can be dated rather than guessed at.
CHECKED_AGAINST_MIGRATION = "V1_410"

# Columns present on nearly every table, written from the audit helper.
AUDIT = ("id", "uuid", "is_voided", "version", "organisation_id",
         "created_by_id", "last_modified_by_id", "created_date_time", "last_modified_date_time")


@dataclass(frozen=True)
class Contract:
    """What the generator writes for one table, and what it knowingly leaves alone."""
    table: str
    populated: frozenset[str]
    # Column -> why it is left unset. A reason is required: "not needed" with no explanation is how
    # a column that mattered gets waved through.
    unwritten: dict[str, str] = field(default_factory=dict)

    @property
    def accounted(self) -> frozenset[str]:
        return self.populated | frozenset(self.unwritten)

    def unaccounted(self, target_columns) -> list[str]:
        """Columns the target has that this contract has never heard of."""
        return sorted(set(target_columns) - self.accounted)

    def missing(self, target_columns) -> list[str]:
        """Columns this contract writes that the target no longer has."""
        return sorted(self.populated - set(target_columns))


def _c(table, populated, unwritten=None, audit=True):
    return Contract(table=table,
                    populated=frozenset(populated) | (frozenset(AUDIT) if audit else frozenset()),
                    unwritten=dict(unwritten or {}))


_SYNC = {
    "sync_concept_1_value": "written -- sync_3 and sync_4 index it",
    "sync_concept_2_value": "written -- sync_4 indexes it",
}

CONTRACTS: dict[str, Contract] = {
    "address_level": _c("address_level",
        ["title", "level", "type_id", "parent_id", "lineage"],
        {"gps_coordinates": "no geospatial query is under test",
         "legacy_id": "import provenance, unused by sync",
         "location_properties": "not read on the sync path",
         "title_lineage": "derived for reporting views, not sync"}),

    "catchment": _c("catchment", ["name"],
        {"type": "unused by sync"}),

    "catchment_address_mapping": _c("catchment_address_mapping",
        ["catchment_id", "addresslevel_id"],
        {"created_date_time": "audit column, and this table is never itself synced",
         "last_modified_date_time": "audit column, and this table is never itself synced",
         "created_by_id": "audit column, nullable, and no sync query reads it",
         "last_modified_by_id": "audit column, nullable, and no sync query reads it",
         "id": "serial -- the sequence assigns it, nothing references it",
         "version": "optimistic-locking counter, only the application increments it",
         "is_voided": "a removed mapping is deleted rather than voided",
         "organisation_id": "this table has no tenant column; scope comes from the catchment",
         "uuid": "this table has no uuid column"}, audit=False),

    "users": _c("users", ["username", "catchment_id", "disabled_in_cognito"],
        {"name": "shown in the admin screens; no sync query reads it",
         "email": "no notification path under test",
         "phone_number": "no notification path under test",
         "settings": "left at the server's own default, which is what production users get",
         "operating_individual_scope": "server default",
         "ignore_sync_settings_in_dea": "server default",
         "sync_settings": "attribute-based sync settings -- see the note in H",
         "last_activated_date_time": "not read on the sync path",
         "lineage": "derived from the catchment by the application, not read by sync",
         "is_org_admin": "field workers and supervisors are not organisation admins",
         "password": "AVNI_IDP_TYPE=none authenticates from the header (B1)",
         "identifier_source_id": "no identifier generation under test",
         "subject_id": "user-subject linkage not modelled"}),

    "individual": _c("individual",
        ["subject_type_id", "address_id", "registration_date", "date_of_birth",
         "date_of_birth_verified", "first_name", "last_name", "observations"] + list(_SYNC),
        {"middle_name": "optional, and name fields are not indexed on the sync path",
         "gender_id": "not read by sync scope resolution",
         "profile_picture": "media is out of scope (D5)",
         "registration_location": "no geospatial query under test",
         "legacy_id": "import provenance",
         "facility_id": "facility linkage not modelled",
         "subject_type": "resolved through subject_type_id"}),

    "program_enrolment": _c("program_enrolment",
        ["program_id", "individual_id", "address_id", "enrolment_date_time", "observations",
         "program_exit_date_time"] + list(_SYNC),
        {"enrolment_location": "no geospatial query under test",
         "exit_location": "no geospatial query under test",
         "program_exit_observations": "exit forms are not part of the modelled workload",
         "legacy_id": "import provenance"}),

    "program_encounter": _c("program_encounter",
        ["program_enrolment_id", "individual_id", "address_id", "encounter_type_id", "name",
         "encounter_date_time", "earliest_visit_date_time", "max_visit_date_time", "observations",
         "cancel_date_time", "sync_disabled"] + list(_SYNC),
        {"cancel_observations": "cancellation forms are not part of the modelled workload",
         "encounter_location": "no geospatial query under test",
         "cancel_location": "no geospatial query under test",
         "sync_disabled_date_time": "only set when sync_disabled is true",
         "legacy_id": "import provenance"}),

    "encounter": _c("encounter",
        ["individual_id", "address_id", "encounter_type_id", "name", "encounter_date_time",
         "earliest_visit_date_time", "max_visit_date_time", "observations", "cancel_date_time",
         "sync_disabled"] + list(_SYNC),
        {"cancel_observations": "cancellation forms are not part of the modelled workload",
         "encounter_location": "no geospatial query under test",
         "cancel_location": "no geospatial query under test",
         "sync_disabled_date_time": "only set when sync_disabled is true",
         "legacy_id": "import provenance"}),
}


class SchemaDrift(RuntimeError):
    """The target's schema and the generator's contract disagree."""


def verify(table: str, target_columns) -> None:
    """Refuse to load unless every column in the target is accounted for.

    Raises rather than warning. A warning in a load script is a warning nobody reads, and the
    failure it guards against produces data that looks fine and measures the wrong thing.
    """
    contract = CONTRACTS.get(table)
    if contract is None:
        raise SchemaDrift(
            f"no contract for table {table!r}. Add one to schema.CONTRACTS saying which columns "
            f"the generator writes and why the rest are left alone.")

    problems = []
    unaccounted = contract.unaccounted(target_columns)
    if unaccounted:
        problems.append(
            f"columns the generator has never heard of: {unaccounted}. A migration since "
            f"{CHECKED_AGAINST_MIGRATION} probably added them. For each one, decide whether the "
            f"generator should write it -- if sync reads or indexes it, the answer is yes -- and "
            f"either populate it or record it in `unwritten` with the reason.")
    missing = contract.missing(target_columns)
    if missing:
        problems.append(
            f"columns the generator writes that the target no longer has: {missing}. Renamed or "
            f"dropped by a migration.")
    if problems:
        raise SchemaDrift(f"{table}: " + " ".join(problems))


def verify_all(target: dict) -> None:
    """Verify every table in one pass, reporting all of them rather than the first."""
    errors = []
    for table, columns in target.items():
        try:
            verify(table, columns)
        except SchemaDrift as e:
            errors.append(str(e))
    if errors:
        raise SchemaDrift("\n\n".join(errors))
