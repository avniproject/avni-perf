"""Assemble a whole deployment: many tenants, one growth point, one dataset.

The test scenarios specify the shape -- two state tenants of 500 field workers, eight NGO tenants
sharing 500, at day 60, 120, 180 or 365. This turns that into files a `COPY` can load.

Two things it has to get right that the per-tenant pieces do not.

**Ids cannot collide across tenants.** Every tenant builds its own locations, catchments, users and
rows, and they all land in the same tables. Each tenant gets a disjoint range per table, wide enough
that a tenant growing does not run into the next one's.

**Nothing is held in memory.** The full pilot dataset at day 180 is around 6.9 million rows. Rows are
generated and written as they go, so the peak cost is one village's subjects rather than a
deployment's.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterator

import catchments as cat
import copy_writer as cw
import hierarchy as hy
import rows as row_gen
from bundle import Bundle
from profile import Profile

# Wide enough that a tenant reaching ten times its planned size still cannot reach its neighbour's
# range. Cheap: ids are bigints.
ID_STRIDE = 100_000_000


@dataclass(frozen=True)
class TenantSpec:
    """One organisation, sized by its field worker count."""
    name: str
    organisation_id: int
    field_workers: int
    field_workers_per_village: int = 3
    beneficiaries_per_village: int = 3000
    encounters_per_worker_per_day: int = 20
    supervisor_level: str = "Sub-Centre"
    # Field workers under one supervisor. None uses the measured establishment -- 2.8 villages to
    # a sub-centre, so about 8.4 workers each. The customer's range is 8 to 20; sweeping it is the
    # point, because the span sets both how many supervisors exist and how heavy each one's sync
    # is. See hierarchy.with_supervisor_span.
    workers_per_supervisor: float | None = None
    # Each tenant may carry its own implementation bundle. H1 makes organisation complexity a load
    # variable in its own right: the number of entities a config defines is the number of rows the
    # client posts to syncDetails, and therefore the number of per-row queries
    # filterChangedEntities runs (D1.1). A small config will not exercise that; a large one will.
    # None falls back to the deployment's bundle.
    bundle_path: str | None = None
    # Co-tenants are sized by the data they hold rather than by a daily encounter rate, because
    # their history is not being modelled -- only their weight in the tables. Set this and it
    # replaces the rate derivation entirely.
    total_encounters: int | None = None

    @property
    def villages(self) -> int:
        return max(1, round(self.field_workers / self.field_workers_per_village))

    @property
    def beneficiaries(self) -> int:
        return self.villages * self.beneficiaries_per_village

    def encounters(self, days: int) -> int:
        if self.total_encounters is not None:
            return self.total_encounters
        return self.field_workers * self.encounters_per_worker_per_day * days


@dataclass(frozen=True)
class DeploymentSpec:
    """One deployment at one growth point."""
    tenants: tuple[TenantSpec, ...]
    days: int
    reference: date
    seed: int = 42
    # Share of subjects enrolled in a programme. Q3's per-device medians give roughly 100
    # enrolments to 464 subjects, so 0.22 is the measured ratio rather than a guess -- but it is a
    # ratio of medians, not a measurement of enrolment rate, and the customer has not supplied one.
    enrolment_rate: float = 0.22
    # Split of encounters between the programme path and the general one. Q3's medians give 89
    # program encounters to 62 encounters per device.
    program_encounter_share: float = 0.59

    @property
    def field_workers(self) -> int:
        return sum(t.field_workers for t in self.tenants)

    @property
    def beneficiaries(self) -> int:
        return sum(t.beneficiaries for t in self.tenants)

    @property
    def encounters(self) -> int:
        return sum(t.encounters(self.days) for t in self.tenants)


def pilot_deployment(days: int, reference: date, *, state_tenants: int = 2,
                     ngo_tenants: int = 8, state_workers: int = 500,
                     ngo_workers_total: int = 500, seed: int = 42) -> DeploymentSpec:
    """The customer's pilot deployment, with the test cases' numbers as the defaults.

    Two state tenants of 500 field workers and eight NGO tenants sharing 500. Named for what it is
    rather than for the plan section that specifies it, because sections move -- this one already
    has, from the plan into test-scenarios.md.
    """
    tenants = []
    for i in range(state_tenants):
        tenants.append(TenantSpec(name=f"state-{i + 1}", organisation_id=i + 1,
                                  field_workers=state_workers))
    per_ngo = max(1, round(ngo_workers_total / ngo_tenants)) if ngo_tenants else 0
    for i in range(ngo_tenants):
        tenants.append(TenantSpec(name=f"ngo-{i + 1}", organisation_id=state_tenants + i + 1,
                                  field_workers=per_ngo))
    return DeploymentSpec(tenants=tuple(tenants), days=days, reference=reference, seed=seed)


@dataclass
class TenantBuild:
    """One tenant's locations, catchments and users, before any transactional rows."""
    spec: TenantSpec
    hierarchy: hy.Hierarchy
    catchments: list[cat.CatchmentSpec]
    users: list[cat.UserSpec]
    id_base: int

    @property
    def villages(self) -> list:
        return self.hierarchy.leaves


def build_tenant(spec: TenantSpec, id_base: int) -> TenantBuild:
    establishment = (hy.ESTABLISHMENT if spec.workers_per_supervisor is None
                     else hy.with_supervisor_span(spec.workers_per_supervisor,
                                                  spec.field_workers_per_village))
    h = hy.build(spec.organisation_id, spec.villages, first_id=id_base + 1,
                 establishment=establishment)
    cs, us = cat.plan(h, field_workers_per_leaf=spec.field_workers_per_village,
                      supervisor_level=spec.supervisor_level,
                      first_catchment_id=id_base + 1, first_user_id=id_base + 1,
                      username_prefix=f"{spec.name}-u")
    return TenantBuild(spec=spec, hierarchy=h, catchments=cs, users=us, id_base=id_base)


def location_rows(build: TenantBuild) -> Iterator[dict]:
    h = build.hierarchy
    for l in h.locations:
        yield {"id": l.id, "uuid": l.uuid, "title": l.title, "level": float(l.depth),
               "type_id": l.type_id, "parent_id": l.parent_id, "lineage": h.lineage(l),
               "organisation_id": l.organisation_id, "is_voided": False, "version": 0,
               "created_by_id": 1, "last_modified_by_id": 1,
               "created_date_time": None, "last_modified_date_time": None}


def transactional_rows(build: TenantBuild, deployment: DeploymentSpec, ctx: row_gen.Context,
                       *, id_base: int) -> dict[str, Iterator[dict]]:
    """Subjects, enrolments and encounters for one tenant, generated village by village.

    Encounters are spread across the village's own subjects, because that is what a shared
    catchment means: every worker in the village records against the same population, and every
    worker then pulls all of it.
    """
    spec = build.spec
    total_encounters = spec.encounters(deployment.days)
    per_village = total_encounters // max(1, spec.villages)
    prog_share = deployment.program_encounter_share

    def generate():
        rng = random.Random(deployment.seed ^ spec.organisation_id)
        subject_id = id_base
        enrolment_id = id_base
        encounter_id = id_base
        prog_encounter_id = id_base
        subject_type = ctx.subject_types[0]

        for village in build.villages:
            scope = row_gen.AddressScope(address_ids=(village.id,))
            subjects, enrolments = [], []

            for _ in range(spec.beneficiaries_per_village):
                subject_id += 1
                s = row_gen.individual(ctx, scope, subject_type, rng) | {"id": subject_id}
                subjects.append(s)
                yield "individual", s

                if ctx.programs and rng.random() < deployment.enrolment_rate:
                    enrolment_id += 1
                    program = rng.choice(ctx.programs)
                    e = row_gen.program_enrolment(ctx, s, program, rng) | {"id": enrolment_id}
                    enrolments.append(e)
                    yield "program_enrolment", e

            for _ in range(per_village):
                if enrolments and rng.random() < prog_share:
                    prog_encounter_id += 1
                    yield "program_encounter", row_gen.program_encounter(
                        ctx, rng.choice(enrolments), rng.choice(ctx.encounter_types), rng
                    ) | {"id": prog_encounter_id}
                elif subjects:
                    encounter_id += 1
                    yield "encounter", row_gen.encounter(
                        ctx, rng.choice(subjects), rng.choice(ctx.encounter_types), rng
                    ) | {"id": encounter_id}

    return generate


def plan_ids(deployment: DeploymentSpec) -> dict[int, int]:
    """A disjoint id range per tenant, so rows from different tenants cannot collide."""
    return {t.organisation_id: i * ID_STRIDE for i, t in enumerate(deployment.tenants)}


def summarise(deployment: DeploymentSpec) -> str:
    lines = [f"deployment: {len(deployment.tenants)} tenants at day {deployment.days}", "",
             f"  {'tenant':<10} {'workers':>8} {'villages':>9} {'beneficiaries':>14} "
             f"{'encounters':>12}"]
    for t in deployment.tenants:
        lines.append(f"  {t.name:<10} {t.field_workers:>8,} {t.villages:>9,} "
                     f"{t.beneficiaries:>14,} {t.encounters(deployment.days):>12,}")
    lines += ["", f"  {'TOTAL':<10} {deployment.field_workers:>8,} "
                  f"{sum(t.villages for t in deployment.tenants):>9,} "
                  f"{deployment.beneficiaries:>14,} {deployment.encounters:>12,}"]
    return "\n".join(lines)


class _Sink:
    """Per-table append-only writers, so tenants stream into shared files."""

    def __init__(self, directory: Path, columns: dict[str, list[str]]):
        self.directory = directory
        self.columns = columns
        self._handles: dict[str, object] = {}
        self.counts: dict[str, int] = {t: 0 for t in columns}

    def __enter__(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        for table in self.columns:
            self._handles[table] = (self.directory / f"{table}.tsv").open(
                "w", encoding="utf-8", newline="\n")
        return self

    def write(self, table: str, row: dict) -> None:
        cols = self.columns.get(table)
        if cols is None:
            raise KeyError(f"no column list for {table!r}; the target schema did not report it")
        fh = self._handles[table]
        fh.write("\t".join(cw.project(row, cols, table=table)))
        fh.write("\n")
        self.counts[table] += 1

    def __exit__(self, *exc):
        for fh in self._handles.values():
            fh.close()


def write_dataset(deployment: DeploymentSpec, bundle: Bundle | dict[int, Bundle],
                  profile: Profile,
                  columns: dict[str, list[str]], directory: str | Path,
                  *, subject_types, programs, encounter_types,
                  verify_schema: bool = True, recipe_name: str | None = None,
                  hash_files: bool = True) -> dict[str, int]:
    """Generate and write a whole deployment. Returns the row count per table.

    Rows stream to disk as they are produced, so the peak memory cost is one village's subjects
    rather than the deployment's 6.9 million rows.
    """
    directory = Path(directory)
    if verify_schema:
        import schema
        schema.verify_all(columns)

    clocks = {t: row_gen.Clock(reference=deployment.reference, age_days=ts.age_days,
                               edited_fraction=ts.edited_after_creation_fraction,
                               median_days_to_first_edit=ts.median_days_to_first_edit)
              for t, ts in profile.temporal.items()}
    key_counts = {ft: t.key_count for ft, t in profile.targets.items()}
    bases = plan_ids(deployment)

    with _Sink(directory, columns) as sink:
        for spec in deployment.tenants:
            base = bases[spec.organisation_id]
            build = build_tenant(spec, base)

            for row in location_rows(build):
                sink.write("address_level", row)
            for row in cat.catchment_rows(build.catchments):
                sink.write("catchment", row)
            for row in cat.declared_mappings(build.catchments):
                sink.write("catchment_address_mapping", row)
            for row in cat.user_rows(build.users):
                sink.write("users", row)

            tenant_bundle = (bundle.get(spec.organisation_id)
                             if isinstance(bundle, dict) else bundle)
            if tenant_bundle is None:
                raise KeyError(
                    f"no bundle for organisation {spec.organisation_id} ({spec.name}). Each "
                    f"tenant needs one, either its own or the deployment's.")
            ctx = row_gen.Context(
                bundle=tenant_bundle, organisation_id=spec.organisation_id,
                subject_types=subject_types, programs=programs,
                encounter_types=encounter_types, clocks=clocks,
                key_counts=key_counts, reference=deployment.reference)
            for table, row in transactional_rows(build, deployment, ctx, id_base=base)():
                sink.write(table, row)

        counts = dict(sink.counts)

    (directory / "load.sql").write_text(
        cw.load_script(columns, directory=str(directory), verify_schema=verify_schema))
    (directory / "summary.txt").write_text(
        summarise(deployment) + "\n\nwritten:\n" +
        "\n".join(f"  {t:<28} {n:>12,}" for t, n in sorted(counts.items())) + "\n")

    # The fingerprint a rebuild is checked against. Row counts alone would miss a change that
    # keeps the counts and alters the content, which is most changes to the generator.
    import recipe as recipe_mod
    recipe_mod.Manifest.of(recipe_name or "(unnamed)", directory, counts,
                           hash_files=hash_files).save(directory / "manifest.json")
    return counts


def feeder_csv(deployment: DeploymentSpec, path: str | Path, *,
               supervisor_push_scale: float = 1.0) -> int:
    """The simulation's `sync-users.csv`, spanning every tenant (E4).

    **The columns are the simulation's contract, not this module's convenience.** It reads
    `userName`, `lastModifiedDateTime`, `password|token` and `pushScale`; anything else is
    ignored. An earlier version of this function emitted `deviceId`, `role` and
    `organisationUUID` and omitted the last two, so a generated feeder silently lost per-user
    push volume and could not be used with `AUTH_MODE=cognito` at all. `role` and
    `organisationUUID` are kept because they are useful when reading the file by hand, and the
    simulation ignores unknown columns.

    **`supervisor_push_scale=1.0` is not a neutral default and should not be read as one.**
    `pushScale` multiplies the drawn record count, and the customer profile's base distribution is
    a field worker's twenty encounters a day. So 1.0 makes every supervisor push exactly as much
    as a field worker, which the deployment says is wrong in a known direction: a supervisor pulls
    a wide catchment and creates almost nothing.

    It is left at 1.0 only because no measurement supports a better number, and a guess would be
    just as fabricated while looking more authoritative. Callers should set it. The overstatement
    is about 11% of total write load in the mixed cases, where supervisors are 62 of 562 users,
    and **all** of it in case 3, which runs supervisors alone.
    """
    import csv
    bases = plan_ids(deployment)
    path = Path(path)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["userName", "lastModifiedDateTime", "password|token",
                                           "pushScale", "deviceId", "role", "organisationUUID"])
        w.writeheader()
        n = 0
        for spec in deployment.tenants:
            build = build_tenant(spec, bases[spec.organisation_id])
            for u in build.users:
                w.writerow({"userName": u.username,
                            "lastModifiedDateTime": "1900-01-01T00:00:00.000Z",
                            "password|token": "",
                            "pushScale": (supervisor_push_scale
                                          if u.role == cat.SUPERVISOR else 1.0),
                            "deviceId": u.device_id, "role": u.role,
                            "organisationUUID": f"org-{spec.organisation_id}"})
                n += 1
    return n
