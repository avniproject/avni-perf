import sys, tempfile
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import bundle as bundle_mod
import deployment as dep
import fixture
import profile as profile_mod
import rows as row_gen
import schema

REFERENCE = date(2026, 9, 18)


def tiny():
    """Two tenants of a few workers. The E6 shape at a size a test can run."""
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


# --- E6's shape -------------------------------------------------------------

def test_the_default_deployment_matches_e6():
    d = dep.e6_deployment(180, REFERENCE)
    assert len(d.tenants) == 10
    assert d.beneficiaries == 1_506_000
    assert abs(d.encounters - 5_414_400) / 5_414_400 < 0.01
    state = [t for t in d.tenants if t.name.startswith("state")]
    assert len(state) == 2 and all(t.field_workers == 500 for t in state)
    assert all(t.villages == 167 for t in state)


@pytest.mark.parametrize("days,expected", [(60, 1_795_200), (120, 3_590_400), (180, 5_385_600)])
def test_only_encounter_volume_grows_between_the_three_datasets(days, expected):
    """Beneficiary population does not grow with programme activity (E6)."""
    d = dep.e6_deployment(days, REFERENCE)
    assert d.encounters == expected
    assert d.beneficiaries == 1_506_000


# --- ids --------------------------------------------------------------------

def test_tenants_get_disjoint_id_ranges():
    d = dep.e6_deployment(180, REFERENCE)
    bases = sorted(dep.plan_ids(d).values())
    assert len(set(bases)) == len(bases)
    assert all(b - a >= dep.ID_STRIDE for a, b in zip(bases, bases[1:]))


def test_the_stride_survives_a_tenant_ten_times_its_planned_size():
    d = dep.e6_deployment(180, REFERENCE)
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


def test_a_load_script_and_a_manifest_are_written():
    b, p, st, pr, et = refs()
    out = Path(tempfile.mkdtemp())
    dep.write_dataset(tiny(), b, p, columns(), out,
                      subject_types=st, programs=pr, encounter_types=et)
    assert "\\copy individual" in (out / "load.sql").read_text()
    manifest = (out / "manifest.txt").read_text()
    assert "day 60" in manifest and "individual" in manifest


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
