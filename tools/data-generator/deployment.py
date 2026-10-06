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
import schema
from bundle import Bundle
from profile import Profile

# **The id columns are int4, not bigint, and this scheme does not fit in one.**
#
# `V0_1__CreateTables` declares `id SERIAL PRIMARY KEY` and nothing since widens it, so every id
# has to stay under 2,147,483,647. At a stride of 100,000,000 only **21 tenants** fit. The pilot
# deployment has ten and reaches 1.0 billion, which is fine; the co-tenant deployment has 513 and
# reaches **51.3 billion**, which is 24x over the ceiling.
#
# So every case needing co-tenant data -- 6, 7, 12 and 13 -- would have failed at load with
# "integer out of range", somewhere around the twenty-second tenant. Found when a bootstrap user
# with a deliberately high id hit the same wall on a real database.
#
# **Not fixed by shrinking this constant**, which only trades one ceiling for another: 513 tenants
# inside int4 allows about 4 million ids each, and a state tenant already needs 1.8 million at day
# 180 with no headroom for growth. The fix is to allocate from each tenant's actual size rather
# than from a fixed block, and it is deliberately not bundled into the change that found it.
INT4_MAX = 2_147_483_647

# **A tenant's band is sized to the tenant, not to the largest one imaginable.**
#
# It used to be a flat 100,000,000 apiece. That survives ten tenants and nothing wider: the
# committed co-tenant deployment has 513 and reached 51.3 billion against int4's 2.147 billion,
# which blocked cases 6, 7, 12 and 13 outright. The stride was sized for a tenant holding millions
# of rows and applied equally to 300 tenants holding one subject each.
#
# Sized per tenant, the whole co-tenant set needs about 7 million ids -- less than the old stride
# gave a single organisation.
ID_BAND_SAFETY = 2      # headroom over the tenant's largest table
ID_BAND_MIN = 10_000    # floor, so a one-subject tenant still has room for its structural rows

# Kept because a generated dataset is often loaded beside an organisation that already holds rows,
# and callers reason in round numbers about how far to shift it. Nothing allocates with it now.
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
    # **A committed recipe cannot name a bundle, so it names an archetype.** The bundles are not
    # in this repository -- they are production exports -- and their filenames are organisation
    # names, which must not appear in a tracked file. A tenant therefore records which *kind* of
    # configuration it is built from, and `--bundle-root` supplies the directory holding one
    # extracted bundle per archetype. The mapping from archetype to organisation stays local.
    #
    # Resolution order is bundle_path, then archetype under the root, then the deployment's own
    # bundle -- so an explicit path still wins and nothing that worked before changes.
    bundle_archetype: str | None = None
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
    # Shifts every tenant's id range up, for generating into an organisation that already holds
    # rows in the tables below -- a bundle brings its own locations and catchments. Must leave
    # room for the tenants above it: id_base + tenants x ID_STRIDE has to stay under INT4_MAX.
    id_base: int = 0
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


def build_tenant(spec: TenantSpec, id_base: int, address_level_types=None,
                 registration_type_ids=None) -> TenantBuild:
    """`address_level_types` comes from refs.json and is what makes the generated locations
    reference type ids that actually exist on the target. Omitted, the tree keeps its measured
    shape and each level's depth doubles as its type id — correct only on an empty database."""
    type_ids = None
    if address_level_types:
        establishment, type_ids = hy.from_target_types(
            address_level_types, registration_type_ids=registration_type_ids)
        if spec.workers_per_supervisor is not None:
            establishment = hy.with_supervisor_span(
                spec.workers_per_supervisor, spec.field_workers_per_village, establishment)
    else:
        establishment = (hy.ESTABLISHMENT if spec.workers_per_supervisor is None
                         else hy.with_supervisor_span(spec.workers_per_supervisor,
                                                      spec.field_workers_per_village))
    h = hy.build(spec.organisation_id, spec.villages, first_id=id_base + 1,
                 establishment=establishment, type_ids=type_ids)
    cs, us = cat.plan(h, field_workers_per_leaf=spec.field_workers_per_village,
                      supervisor_level=spec.supervisor_level,
                      first_catchment_id=id_base + 1, first_user_id=id_base + 1,
                      username_prefix=f"{spec.name}-u")
    return TenantBuild(spec=spec, hierarchy=h, catchments=cs, users=us, id_base=id_base)


def location_rows(build: TenantBuild) -> Iterator[dict]:
    h = build.hierarchy
    for l in h.locations:
        # No `level` column on this table — depth lives in `lineage` and in the type. The name
        # column is `title`, not `name`, which is the opposite of address_level_type.
        yield {"id": l.id, "uuid": l.uuid, "title": l.title,
               "type_id": l.type_id, "parent_id": l.parent_id, "lineage": h.lineage(l),
               "organisation_id": l.organisation_id, "is_voided": False, "version": 0,
               "created_by_id": 1, "last_modified_by_id": 1,
               # Not None. These tables carry a BEFORE INSERT trigger that copies the row's
               # timestamps into `audit`, whose date columns are NOT NULL with no default, so a
               # null here fails the insert with a message naming `audit` rather than this table.
               **cat._stamps()}


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


def band_width(tenant: TenantSpec, days: int) -> int:
    """How much id space one tenant needs.

    Every table the generator writes numbers from the tenant's base with its own counter, so the
    highest id a tenant reaches is its largest table. Doubling that leaves room for a table to
    grow without the bands being replanned, and the floor covers a tenant whose transactional
    tables are nearly empty but which still writes locations, catchments and users.
    """
    return max(ID_BAND_MIN, ID_BAND_SAFETY * max(
        tenant.beneficiaries, tenant.encounters(days),
        tenant.villages * 2, tenant.field_workers * 2))


def plan_ids(deployment: DeploymentSpec) -> dict[int, int]:
    """A disjoint id range per tenant, so rows from different tenants cannot collide.

    `id_base` shifts the whole allocation up. It exists because a generated dataset does not
    always land in an empty organisation: an implementation bundle creates address level types,
    locations and catchments of its own, and those are tables the generator also writes. Starting
    at 1 would collide with them. Default 0 keeps the original behaviour for a clean target.
    """
    bases: dict[int, int] = {}
    cursor = deployment.id_base
    for t in deployment.tenants:
        bases[t.organisation_id] = cursor
        cursor += band_width(t, deployment.days)

    # Refused rather than clamped: an allocation that does not fit is not something to paper over
    # inside an id allocator. The ids would reach the .tsv files, generation would report success,
    # and `COPY` would fail on "integer out of range" -- or load and collide on a column somebody
    # had since widened.
    if cursor > INT4_MAX:
        raise ValueError(
            f"{len(deployment.tenants)} tenants need ids up to {cursor:,}, and these columns are "
            f"int4 (max {INT4_MAX:,}). Bands are sized per tenant, so this is genuinely too much "
            f"data rather than a stride that is too wide: "
            f"{deployment.beneficiaries + deployment.encounters:,} rows across the deployment.")
    return bases


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


def _contract_columns(table: str, target_columns) -> list[str]:
    """The contract's populated set, in the target's column order."""
    populated = schema.CONTRACTS[table].populated
    return [c for c in cw.column_names(target_columns) if c in populated]


class _Sink:
    """Per-table append-only writers, so tenants stream into shared files."""

    def __init__(self, directory: Path, columns: dict[str, list[str]]):
        self.directory = directory
        self.columns = columns
        self._handles: dict[str, object] = {}
        self.counts: dict[str, int] = {t: 0 for t in columns}
        # Narrowed to what the first row of each table actually populates. A column left out
        # takes the server's default; one written as `\N` does not, because COPY reads that as
        # an explicit NULL. See copy_writer.written_columns.
        self.written: dict[str, list[str]] = {}

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
        written = self.written.get(table)
        if written is None:
            written = self.written[table] = cw.written_columns(cols, row)
        fh = self._handles[table]
        fh.write("\t".join(cw.project(row, written, table=table)))
        fh.write("\n")
        self.counts[table] += 1

    def __exit__(self, *exc):
        for fh in self._handles.values():
            fh.close()


def _load_columns(sink, columns):
    """The columns each load script declares: exactly what was written.

    A table with no rows has nothing to narrow against, so it falls back to what its contract says
    it populates rather than to every column the target has -- otherwise an empty file would be
    declared with columns nothing ever writes, `audit_id` among them.
    """
    return {t: sink.written.get(t) or _contract_columns(t, columns[t]) for t in columns}


def write_dataset(deployment: DeploymentSpec, bundle: Bundle | dict[int, Bundle],
                  profile: Profile,
                  columns: dict[str, list[str]], directory: str | Path,
                  *, subject_types, programs, encounter_types,
                  verify_schema: bool = True, recipe_name: str | None = None,
                  hash_files: bool = True, address_level_types=None,
                  registration_type_ids=None) -> dict[str, int]:
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
            build = build_tenant(spec, base, address_level_types, registration_type_ids)

            for row in location_rows(build):
                sink.write("address_level", row)
            for row in cat.catchment_rows(build.catchments):
                sink.write("catchment", row)
            for row in cat.declared_mappings(build.catchments):
                sink.write("catchment_address_mapping", row)
            for row in cat.user_rows(build.users):
                sink.write("users", row)
            # Group membership, without which these users resolve no privileges and sync none of
            # the data generated below them. One group per organisation, so it is written here
            # with the tenant rather than once globally.
            group_ids = {spec.organisation_id: cat.group_id_for(base)}
            for row in cat.group_rows(group_ids):
                sink.write("groups", row)
            for row in cat.user_group_rows(build.users, group_ids=group_ids):
                sink.write("user_group", row)

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
        # The load script names exactly the columns that were written, not every column the
        # target has -- otherwise `\copy` would expect values the files do not contain.
        # A table with no rows has nothing to narrow against, so it falls back to what its
        # contract says it populates rather than to every column the target has -- otherwise an
        # empty file would be declared with columns nothing ever writes, `audit_id` among them.
        cw.load_script(_load_columns(sink, columns),
                       directory=str(directory), verify_schema=verify_schema))
    # The transactional half, for restoring after a per-run TRUNCATE. G4 settled on that as the
    # reset, and reloading the full load.sql afterwards collides on every structural table whose
    # rows the truncate deliberately left alone.
    (directory / "reload.sql").write_text(
        cw.reload_script(_load_columns(sink, columns),
                         directory=str(directory), verify_schema=verify_schema))
    (directory / "summary.txt").write_text(
        summarise(deployment) + "\n\nwritten:\n" +
        "\n".join(f"  {t:<28} {n:>12,}" for t, n in sorted(counts.items())) + "\n")

    # The fingerprint a rebuild is checked against. Row counts alone would miss a change that
    # keeps the counts and alters the content, which is most changes to the generator.
    import recipe as recipe_mod
    recipe_mod.Manifest.of(recipe_name or "(unnamed)", directory, counts,
                           hash_files=hash_files,
                           target={"organisations": [t.organisation_id for t in deployment.tenants],
                                   "id_base": deployment.id_base}
                           ).save(directory / "manifest.json")
    return counts


# The simulation's contract, in one place because two writers emit it: this module for a generated
# deployment and `bootstrap_user.py` for a cohort with no dataset behind it. It drifted once when
# only one of them knew the list -- `pushScale` was missing and its absence is silent, since a null
# column reads as 1.0.
FEEDER_FIELDS = ["userName", "lastModifiedDateTime", "password|token", "pushScale",
                 "deviceId", "role", "organisationUUID"]


def feeder_csv(deployment: DeploymentSpec, path: str | Path, *,
               supervisor_push_scale: float = 1.0, address_level_types=None,
               registration_type_ids=None, refs_by_organisation=None) -> int:
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

    **`refs_by_organisation` maps organisation_id to that tenant's `(address_level_types,
    registration_type_ids)`** and wins over the single-value arguments. It matters because the
    usernames here have to be the ones already in the database: `build_tenant` derives the
    hierarchy from the target's own address level types, `from_target_types` truncates it at the
    deepest permitted registration type, and villages, catchments and therefore users all follow.
    Build the feeder from different refs than the load used and the file is still well-formed --
    every row just names a user the server has never heard of.
    """
    import csv
    bases = plan_ids(deployment)
    path = Path(path)
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FEEDER_FIELDS)
        w.writeheader()
        n = 0
        for spec in deployment.tenants:
            # Per-tenant refs win. Tenants on different bundles have different address level
            # types, and `build_tenant` derives the hierarchy from them -- so a feeder built from
            # one tenant's refs would name users that do not exist in the others. That is silent:
            # the file is well-formed and every row 401s or syncs an empty catchment.
            alts, reg = address_level_types, registration_type_ids
            if refs_by_organisation and spec.organisation_id in refs_by_organisation:
                alts, reg = refs_by_organisation[spec.organisation_id]
            build = build_tenant(spec, bases[spec.organisation_id], alts, reg)
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
