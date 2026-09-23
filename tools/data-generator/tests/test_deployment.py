import sys, tempfile
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import bundle as bundle_mod
import catchments as cat
import deployment as dep
import fixture
import profile as profile_mod
import rows as row_gen
import schema

REFERENCE = date(2026, 9, 18)


def tiny():
    """Two tenants of a few workers. The pilot shape at a size a test can run."""
    return dep.DeploymentSpec(
        tenants=(dep.TenantSpec(name="a", organisation_id=1, field_workers=6,
                                beneficiaries_per_village=5),
                 dep.TenantSpec(name="b", organisation_id=2, field_workers=3,
                                beneficiaries_per_village=5)),
        days=60, reference=REFERENCE, seed=7)


def refs():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    return (bundle_mod.load(d), profile_mod.load(),
            [row_gen.SubjectTypeRef(id=1, uuid=fixture.SUBJECT_TYPE, name="P",
                                    sync_concept_1=fixture.CODED)],
            [row_gen.ProgramRef(id=7, uuid="prog", name="Programme")],
            [row_gen.EncounterTypeRef(id=9, uuid="et", name="Visit")])


def columns():
    """Column lists as a target database would report them, contract-clean."""
    return {t: sorted(c.accounted) for t, c in schema.CONTRACTS.items()}


# --- the pilot's shape -------------------------------------------------------------

def test_the_default_deployment_matches_e6():
    d = dep.pilot_deployment(180, REFERENCE)
    assert len(d.tenants) == 10
    assert d.beneficiaries == 1_506_000
    assert abs(d.encounters - 5_414_400) / 5_414_400 < 0.01
    state = [t for t in d.tenants if t.name.startswith("state")]
    assert len(state) == 2 and all(t.field_workers == 500 for t in state)
    assert all(t.villages == 167 for t in state)


@pytest.mark.parametrize("days,expected", [(60, 1_795_200), (120, 3_590_400), (180, 5_385_600)])
def test_only_encounter_volume_grows_between_the_three_datasets(days, expected):
    """Beneficiary population does not grow with programme activity (test scenarios)."""
    d = dep.pilot_deployment(days, REFERENCE)
    assert d.encounters == expected
    assert d.beneficiaries == 1_506_000


# --- ids --------------------------------------------------------------------

def test_tenants_get_disjoint_id_ranges():
    d = dep.pilot_deployment(180, REFERENCE)
    bases = sorted(dep.plan_ids(d).values())
    assert len(set(bases)) == len(bases)
    assert all(b - a >= dep.ID_STRIDE for a, b in zip(bases, bases[1:]))


def test_the_stride_survives_a_tenant_ten_times_its_planned_size():
    d = dep.pilot_deployment(180, REFERENCE)
    biggest = max(t.beneficiaries + t.encounters(180) for t in d.tenants)
    assert biggest * 10 < dep.ID_STRIDE, "a tenant could reach its neighbour's range"


def test_no_id_collides_across_tenants_in_a_real_run():
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    dep.write_dataset(tiny(), b, p, columns(), out,
                      subject_types=st, programs=pr, encounter_types=et)
    for table in ("address_level", "individual", "users"):
        cols = sorted(schema.CONTRACTS[table].accounted)
        idx = cols.index("id")
        ids = [ln.split("\t")[idx] for ln in
               (out / f"{table}.tsv").read_text().splitlines()]
        assert len(ids) == len(set(ids)), f"{table} has duplicate ids across tenants"


# --- writing ----------------------------------------------------------------

def test_every_table_is_written_and_counted():
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    counts = dep.write_dataset(tiny(), b, p, columns(), out,
                               subject_types=st, programs=pr, encounter_types=et)
    spec = tiny()
    expected_subjects = sum(t.villages * t.beneficiaries_per_village for t in spec.tenants)
    assert counts["individual"] == expected_subjects
    assert counts["address_level"] > 0 and counts["users"] > 0
    assert counts["program_encounter"] + counts["encounter"] > 0
    for table in counts:
        assert (out / f"{table}.tsv").exists()


def test_a_load_script_a_summary_and_a_manifest_are_written():
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    counts = dep.write_dataset(tiny(), b, p, columns(), out,
                               subject_types=st, programs=pr, encounter_types=et,
                               recipe_name="tiny")
    assert "\\copy individual" in (out / "load.sql").read_text()

    summary = (out / "summary.txt").read_text()
    assert "day 60" in summary and "individual" in summary

    import recipe as recipe_mod
    m = recipe_mod.Manifest.load(out / "manifest.json")
    assert m.recipe == "tiny"
    assert m.total_rows == sum(counts.values())
    assert m.tables["individual"]["sha256"]


def test_the_manifest_is_a_fingerprint_a_rebuild_is_checked_against():
    """Row counts alone would miss a change that keeps the counts and alters the content, which is
    most changes to the generator."""
    b, p, st, pr, et = refs()
    import recipe as recipe_mod
    built = []
    for seed in (7, 8):
        out = Path(tempfile.mkdtemp())
        spec = dep.DeploymentSpec(tenants=tiny().tenants, days=60,
                                  reference=REFERENCE, seed=seed)
        dep.write_dataset(spec, b, p, columns(), out, subject_types=st, programs=pr,
                          encounter_types=et, recipe_name="tiny")
        built.append(recipe_mod.Manifest.load(out / "manifest.json"))
    diffs = built[0].differences(built[1])
    assert diffs, "a different seed must show up as a difference"
    assert any("different content" in d for d in diffs)


def test_the_write_refuses_a_schema_it_does_not_recognise():
    b, p, st, pr, et = refs()
    cols = columns()
    cols["individual"] = cols["individual"] + ["column_from_a_later_migration"]
    with pytest.raises(schema.SchemaDrift):
        dep.write_dataset(tiny(), b, p, cols, Path(tempfile.mkdtemp()),
                          subject_types=st, programs=pr, encounter_types=et)


def test_generation_is_reproducible_for_a_seed():
    b, p, st, pr, et = refs()
    outs = []
    for _ in range(2):
        o = Path(tempfile.mkdtemp())
        dep.write_dataset(tiny(), b, p, columns(), o,
                          subject_types=st, programs=pr, encounter_types=et)
        outs.append((o / "individual.tsv").read_text())
    assert outs[0] == outs[1]


def test_the_feeder_spans_every_tenant():
    """E4 needs one user file covering the whole deployment, not one per tenant."""
    out = Path(tempfile.mkdtemp()) / "sync-users.csv"
    n = dep.feeder_csv(tiny(), out)
    text = out.read_text()
    assert n > 0
    assert "organisationUUID" in text
    assert "org-1" in text and "org-2" in text
    assert text.count("field_worker") > text.count("supervisor")


def test_the_feeder_carries_every_column_the_simulation_reads():
    """The columns are a contract with the simulation, and it drifted once already.

    `feeder_csv` used to emit deviceId/role/organisationUUID and omit `password|token` and
    `pushScale`. Nothing checked, so a generated feeder silently gave every user the default
    push volume -- the exact failure the pushScale column exists to prevent -- and could not
    be used with AUTH_MODE=cognito at all.

    The committed example file is the documented contract, so this pins the generator to it
    rather than to a list that would have to be remembered separately.
    """
    import csv as _csv
    example = (Path(__file__).resolve().parents[3]
               / "src/gatling/resources/sync-users-example.csv")
    required = set(next(_csv.reader(example.open(encoding="utf-8-sig"))))

    out = Path(tempfile.mkdtemp()) / "sync-users.csv"
    dep.feeder_csv(tiny(), out)
    produced = set(next(_csv.reader(out.open())))

    missing = required - produced
    assert not missing, f"generated feeder is missing {sorted(missing)}"


def test_supervisors_are_not_silently_given_a_field_workers_push_volume():
    """The default is unscaled, and that is deliberate -- no measurement supports a number yet.

    What must not happen is the column going missing again, which would make the distinction
    unexpressable rather than merely unset.
    """
    out = Path(tempfile.mkdtemp()) / "sync-users.csv"
    dep.feeder_csv(tiny(), out, supervisor_push_scale=0.1)
    rows = list(csv_rows(out))
    supervisors = [r for r in rows if r["role"] == "supervisor"]
    workers = [r for r in rows if r["role"] == "field_worker"]
    assert supervisors and workers
    assert all(float(r["pushScale"]) == 0.1 for r in supervisors)
    assert all(float(r["pushScale"]) == 1.0 for r in workers)


def csv_rows(path):
    import csv as _csv
    with Path(path).open() as fh:
        yield from _csv.DictReader(fh)


def test_encounters_reference_only_their_own_tenants_subjects():
    """A shared catchment means a village's workers record against that village's population.
    An encounter pointing at another tenant's subject would break RLS and sync scope alike."""
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    dep.write_dataset(tiny(), b, p, columns(), out,
                      subject_types=st, programs=pr, encounter_types=et)
    icols = sorted(schema.CONTRACTS["individual"].accounted)
    subj = {}
    for ln in (out / "individual.tsv").read_text().splitlines():
        f = ln.split("\t")
        subj[f[icols.index("id")]] = f[icols.index("organisation_id")]
    ecols = sorted(schema.CONTRACTS["encounter"].accounted)
    for ln in (out / "encounter.tsv").read_text().splitlines():
        f = ln.split("\t")
        sid, org = f[ecols.index("individual_id")], f[ecols.index("organisation_id")]
        assert subj.get(sid) == org, f"encounter in org {org} references subject {sid}"


# --- a bundle per tenant ----------------------------------------------------

def two_bundles():
    """Two bundles of different size. H1 makes organisation complexity a load variable: config
    size drives the syncDetails row count and therefore D1.1's per-row queries."""
    import json
    small = Path(tempfile.mkdtemp()); fixture.write(small)
    large = Path(tempfile.mkdtemp()); fixture.write(large)
    # give the second bundle a second mapping, so its reachable surface differs
    mappings = json.loads((large / "formMappings.json").read_text())
    mappings.append({"uuid": "m3", "formUUID": fixture.FORM, "formType": "Encounter",
                     "subjectTypeUUID": fixture.SUBJECT_TYPE})
    (large / "formMappings.json").write_text(json.dumps(mappings))
    return bundle_mod.load(small), bundle_mod.load(large)


def test_each_tenant_can_be_built_from_its_own_bundle():
    _, p, st, pr, et = refs()
    small, large = two_bundles()
    assert len(large.mappings) > len(small.mappings)
    spec = dep.DeploymentSpec(
        tenants=(dep.TenantSpec(name="a", organisation_id=1, field_workers=3,
                                beneficiaries_per_village=4),
                 dep.TenantSpec(name="b", organisation_id=2, field_workers=3,
                                beneficiaries_per_village=4)),
        days=30, reference=REFERENCE)
    out = Path(tempfile.mkdtemp())
    counts = dep.write_dataset(spec, {1: small, 2: large}, p, columns(), out,
                               subject_types=st, programs=pr, encounter_types=et)
    assert counts["individual"] == 8


def test_a_tenant_with_no_bundle_fails_loudly():
    _, p, st, pr, et = refs()
    small, _ = two_bundles()
    spec = dep.DeploymentSpec(
        tenants=(dep.TenantSpec(name="a", organisation_id=1, field_workers=3),
                 dep.TenantSpec(name="b", organisation_id=2, field_workers=3)),
        days=30, reference=REFERENCE)
    with pytest.raises(KeyError, match="no bundle for organisation 2"):
        dep.write_dataset(spec, {1: small}, p, columns(), Path(tempfile.mkdtemp()),
                          subject_types=st, programs=pr, encounter_types=et)


def test_one_bundle_still_covers_every_tenant():
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    counts = dep.write_dataset(tiny(), b, p, columns(), out,
                               subject_types=st, programs=pr, encounter_types=et)
    assert counts["individual"] > 0


def test_a_tenant_spec_records_its_own_bundle():
    t = dep.TenantSpec(name="a", organisation_id=1, field_workers=3, bundle_path="/tmp/x")
    assert t.bundle_path == "/tmp/x"
    assert dep.TenantSpec(name="b", organisation_id=2, field_workers=3).bundle_path is None


def test_supervisor_span_trades_count_against_catchment_size():
    """The 8-to-20 range is a sweep because it moves two things in opposite directions.

    Widening the span means fewer supervisors, each covering more. Total supervisor-pulled volume
    barely changes; its distribution goes from many light syncs to few heavy ones, and a p95
    target only notices the second. If this ever stops holding, the scenarios' user counts and
    per-device tables are both wrong.
    """
    def shape(span):
        spec = dep.TenantSpec(name="s", organisation_id=1, field_workers=500,
                              workers_per_supervisor=span)
        b = dep.build_tenant(spec, 0)
        leaf = b.hierarchy.levels[-1].name
        sups = [c for c in b.catchments if c.role == cat.SUPERVISOR]
        scope = [len([d for d in b.hierarchy.descendants(c.locations[0])
                      if d.level_name == leaf]) for c in sups]
        return len(sups), sum(scope) / len(scope)

    narrow_count, narrow_scope = shape(8)
    wide_count, wide_scope = shape(20)

    assert narrow_count > wide_count, "a wider span must mean fewer supervisors"
    assert wide_scope > narrow_scope, "a wider span must mean a larger catchment each"
    # Villages covered overall stays put -- the same workers are supervised either way.
    assert narrow_count * narrow_scope == pytest.approx(wide_count * wide_scope, rel=0.10)
    # And the span is actually what was asked for, in field workers.
    assert narrow_scope * 3 == pytest.approx(8, abs=0.5)
    assert wide_scope * 3 == pytest.approx(20, abs=0.5)


def test_the_default_span_is_the_measured_establishment():
    """None must leave the tree exactly as it was before the parameter existed."""
    plain = dep.build_tenant(dep.TenantSpec(name="s", organisation_id=1, field_workers=500), 0)
    explicit = dep.build_tenant(
        dep.TenantSpec(name="s", organisation_id=1, field_workers=500,
                       workers_per_supervisor=None), 0)
    assert len(plain.hierarchy.locations) == len(explicit.hierarchy.locations)
    sups = len([c for c in plain.catchments if c.role == cat.SUPERVISOR])
    # 2.8 villages to a sub-centre at three workers each is about 8.4, so roughly 60 of them.
    assert 55 <= sups <= 65, f"measured establishment should give about 60 supervisors, got {sups}"
