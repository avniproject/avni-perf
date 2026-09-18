"""Generate the transactional rows a load test needs, with their observations.

Four tables, in dependency order: individual, program_enrolment, program_encounter, encounter.

Rows come out as column-keyed dicts rather than tuples. The COPY writer projects them onto whatever
columns the target database actually has, because the column list belongs to the database and not to
this file -- migrations accumulate, and a hardcoded list here would rot silently and produce a COPY
that fails or, worse, one that shifts every value one column to the left.

The denormalised sync columns matter more than they look. Each table carries five sync_N indexes,
one per sync strategy:

    sync_1  address_id, last_modified_date_time, organisation_id, ...      sync by location
    sync_2  individual_id, last_modified_date_time, ...                    sync by subject
    sync_3  sync_concept_1_value, last_modified_date_time, ...             by one attribute
    sync_4  sync_concept_1_value, sync_concept_2_value, ...                by two attributes

`individual_sync_2_index` carried 3.48 billion scans in 69 days of production. Leaving address_id or
the sync concept values null means the generated data never touches those indexes, and the query
plans under test stop resembling production's.
"""
from __future__ import annotations

import json
import math
import random
import uuid as uuid_mod
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from bundle import Bundle, FormMapping
from distribution import Quantiles
from observations import KeyCount, generate as generate_observations


@dataclass(frozen=True)
class SubjectTypeRef:
    """A subject type as the generator needs it, resolved from the target database."""
    id: int
    uuid: str
    name: str
    # Concept UUIDs the subject type designates for attribute-based sync, when usable.
    sync_concept_1: str | None = None
    sync_concept_2: str | None = None


@dataclass(frozen=True)
class ProgramRef:
    id: int
    uuid: str
    name: str


@dataclass(frozen=True)
class EncounterTypeRef:
    id: int
    uuid: str
    name: str


@dataclass(frozen=True)
class Catchment:
    """One user's slice of the location hierarchy, and the rows that will sit inside it."""
    user_id: int
    address_ids: tuple[int, ...]

    def address(self, rng: random.Random) -> int:
        return rng.choice(self.address_ids)


@dataclass(frozen=True)
class Clock:
    """Creation and modification timestamps for one table, spread as Q14 measured them.

    Q14 measured the age of `last_modified_date_time`, so that is what gets sampled, and creation is
    derived backwards from it. Doing it the other way round -- picking a creation date and adding an
    edit -- cannot reproduce the measurement, because a row edited long after creation would land
    with an age the measurement never saw.

    A dataset whose rows share one timestamp makes incremental sync return everything or nothing,
    which leaves every incremental scenario measuring nothing at all (H3).
    """
    reference: date
    age_days: Quantiles
    edited_fraction: float = 0.0
    median_days_to_first_edit: float | None = None

    def created_and_modified(self, rng: random.Random) -> tuple[datetime, datetime]:
        modified = self._at(self.reference - timedelta(days=max(self.age_days.sample(rng), 0)), rng)
        if rng.random() >= self.edited_fraction or not self.median_days_to_first_edit:
            return modified, modified
        # Exponential, scaled so its median is the measured median gap. Program encounters sit at
        # 32 days -- the scheduled-visit pattern, booked then filled in -- against 383 to 595
        # elsewhere, which is why this is a per-table input.
        gap_days = rng.expovariate(math.log(2) / self.median_days_to_first_edit)
        created = modified - timedelta(days=gap_days)
        return created, modified

    @staticmethod
    def _at(d: date, rng: random.Random) -> datetime:
        return datetime(d.year, d.month, d.day, rng.randrange(24), rng.randrange(60),
                        rng.randrange(60))


@dataclass
class Context:
    """Everything resolved from the target database and the bundle, in one place."""
    bundle: Bundle
    organisation_id: int
    subject_types: list[SubjectTypeRef]
    programs: list[ProgramRef]
    encounter_types: list[EncounterTypeRef]
    clocks: dict[str, Clock]
    key_counts: dict[str, KeyCount]
    reference: date
    audit_user_id: int = 1
    reference_uuids: dict[str, list[str]] = field(default_factory=dict)

    def mapping(self, form_type: str, *, subject_type_uuid: str | None = None,
                program_uuid: str | None = None,
                encounter_type_uuid: str | None = None) -> FormMapping | None:
        for m in self.bundle.mappings:
            if m.form_type != form_type:
                continue
            if subject_type_uuid and m.subject_type_uuid != subject_type_uuid:
                continue
            if program_uuid and m.program_uuid != program_uuid:
                continue
            if encounter_type_uuid and m.encounter_type_uuid != encounter_type_uuid:
                continue
            return m
        return None

    def observations(self, form_type: str, rng: random.Random, anchor: date, **kw) -> dict:
        mapping = self.mapping(form_type, **kw)
        if mapping is None:
            return {}
        kc = self.key_counts.get(form_type)
        if kc is None:
            return {}
        return generate_observations(self.bundle.elements_for(mapping), kc, rng, anchor,
                                     reference_uuids=self.reference_uuids)


def _audit(ctx: Context, table: str, rng: random.Random) -> dict:
    clock = ctx.clocks.get(table)
    if clock is None:
        raise KeyError(f"no timestamp spread configured for table {table!r}")
    created, modified = clock.created_and_modified(rng)
    return {
        "uuid": str(uuid_mod.uuid4()),
        "is_voided": False,
        "version": 0,
        "organisation_id": ctx.organisation_id,
        "created_by_id": ctx.audit_user_id,
        "last_modified_by_id": ctx.audit_user_id,
        "created_date_time": created,
        "last_modified_date_time": modified,
    }


def _sync_values(subject_type: SubjectTypeRef, observations: dict) -> dict:
    """Denormalise the subject type's designated sync concepts onto the row.

    Mirrors `SyncAttributeEntity.addConceptSyncAttributeValues`, which reads the subject's own
    registration observation and passes it through `ObservationCollection.getAsSingleStringValue`:
    a value that resolves to exactly one entry is stored as that entry, and a multi-valued one is
    stored as the array. Storing a language's own list repr instead would put a value in the column
    that no sync query can ever match.
    """
    out: dict = {"sync_concept_1_value": None, "sync_concept_2_value": None}
    for n, concept_uuid in ((1, subject_type.sync_concept_1), (2, subject_type.sync_concept_2)):
        if not concept_uuid:
            continue
        v = observations.get(concept_uuid)
        if v is None:
            continue
        if isinstance(v, list):
            value = str(v[0]) if len(v) == 1 else json.dumps(v)
        else:
            value = str(v)
        out[f"sync_concept_{n}_value"] = value
    return out


def individual(ctx: Context, catchment: Catchment, subject_type: SubjectTypeRef,
               rng: random.Random) -> dict:
    row = _audit(ctx, "individual", rng)
    obs = ctx.observations("IndividualProfile", rng, ctx.reference,
                           subject_type_uuid=subject_type.uuid)
    registration = (row["created_date_time"]).date()
    row.update({
        "subject_type_id": subject_type.id,
        "address_id": catchment.address(rng),
        "registration_date": registration,
        "date_of_birth": registration - timedelta(days=rng.randrange(0, 80 * 365)),
        "date_of_birth_verified": False,
        "first_name": f"Subject{rng.randrange(10**6):06d}",
        "last_name": f"Family{rng.randrange(10**4):04d}",
        "observations": obs,
    })
    row.update(_sync_values(subject_type, obs))
    return row


def program_enrolment(ctx: Context, subject: dict, program: ProgramRef,
                      rng: random.Random) -> dict:
    row = _audit(ctx, "program_enrolment", rng)
    # An enrolment cannot predate the subject it belongs to.
    if row["created_date_time"] < subject["created_date_time"]:
        row["created_date_time"] = subject["created_date_time"]
        row["last_modified_date_time"] = max(row["last_modified_date_time"],
                                             subject["created_date_time"])
    row.update({
        "program_id": program.id,
        "individual_id": subject["id"],
        "address_id": subject["address_id"],
        "enrolment_date_time": row["created_date_time"],
        "observations": ctx.observations("ProgramEnrolment", rng, ctx.reference,
                                         program_uuid=program.uuid),
        "program_exit_date_time": None,
        "sync_concept_1_value": subject.get("sync_concept_1_value"),
        "sync_concept_2_value": subject.get("sync_concept_2_value"),
    })
    return row


def program_encounter(ctx: Context, enrolment: dict, encounter_type: EncounterTypeRef,
                      rng: random.Random) -> dict:
    row = _audit(ctx, "program_encounter", rng)
    if row["created_date_time"] < enrolment["enrolment_date_time"]:
        row["created_date_time"] = enrolment["enrolment_date_time"]
        row["last_modified_date_time"] = max(row["last_modified_date_time"],
                                             enrolment["enrolment_date_time"])
    row.update({
        "program_enrolment_id": enrolment["id"],
        "individual_id": enrolment["individual_id"],
        "address_id": enrolment["address_id"],
        "encounter_type_id": encounter_type.id,
        "name": encounter_type.name,
        "encounter_date_time": row["created_date_time"],
        "earliest_visit_date_time": None,
        "max_visit_date_time": None,
        "observations": ctx.observations("ProgramEncounter", rng, ctx.reference,
                                         encounter_type_uuid=encounter_type.uuid),
        "cancel_date_time": None,
        "sync_disabled": False,
        "sync_concept_1_value": enrolment.get("sync_concept_1_value"),
        "sync_concept_2_value": enrolment.get("sync_concept_2_value"),
    })
    return row


def encounter(ctx: Context, subject: dict, encounter_type: EncounterTypeRef,
              rng: random.Random) -> dict:
    row = _audit(ctx, "encounter", rng)
    if row["created_date_time"] < subject["created_date_time"]:
        row["created_date_time"] = subject["created_date_time"]
        row["last_modified_date_time"] = max(row["last_modified_date_time"],
                                             subject["created_date_time"])
    row.update({
        "individual_id": subject["id"],
        "address_id": subject["address_id"],
        "encounter_type_id": encounter_type.id,
        "name": encounter_type.name,
        "encounter_date_time": row["created_date_time"],
        "earliest_visit_date_time": None,
        "max_visit_date_time": None,
        "observations": ctx.observations("Encounter", rng, ctx.reference,
                                         encounter_type_uuid=encounter_type.uuid),
        "cancel_date_time": None,
        "sync_disabled": False,
        "sync_concept_1_value": subject.get("sync_concept_1_value"),
        "sync_concept_2_value": subject.get("sync_concept_2_value"),
    })
    return row
