import json, sys, tempfile
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

import deployment as dep
import fixture
import profile as profile_mod
import recipe as recipe_mod
import validate

REFERENCE = date(2026, 9, 18)
DATASETS = Path(__file__).resolve().parents[1] / "datasets"


def a_recipe(**kw):
    d = dep.pilot_deployment(180, REFERENCE)
    return recipe_mod.Recipe.from_deployment(
        "test", d, profile="production-2026-09", bundle_path="/tmp/bundle", **kw)


# --- the committed recipes --------------------------------------------------

@pytest.mark.parametrize("days", [60, 120, 180, 365])
def test_a_committed_recipe_rebuilds_the_deployment_it_describes(days):
    r = recipe_mod.Recipe.load(DATASETS / f"pilot-day-{days}.json")
    d = r.to_deployment()
    reference = dep.pilot_deployment(days, date.fromisoformat(r.reference_date))
    assert d.beneficiaries == reference.beneficiaries
    assert d.encounters == reference.encounters
    assert len(d.tenants) == len(reference.tenants)


def test_the_committed_recipes_differ_only_in_growth_point():
    """Only encounter volume grows between the growth points."""
    rs = {d: recipe_mod.Recipe.load(DATASETS / f"pilot-day-{d}.json") for d in (60, 120, 180, 365)}
    assert {r.days for r in rs.values()} == {60, 120, 180, 365}
    assert len({json.dumps(r.tenants, sort_keys=True) for r in rs.values()}) == 1
    assert len({r.seed for r in rs.values()}) == 1


def test_the_committed_recipes_say_the_bundle_must_be_filled_in():
    """Reproducibility depends on the bundle, which is deliberately not in this repository. A
    recipe without it is a promise the repo cannot keep, so it must not look complete."""
    for days in (60, 120, 180, 365):
        r = recipe_mod.Recipe.load(DATASETS / f"pilot-day-{days}.json")
        assert r.bundle_fingerprint.get("combined") is None
        assert "must be filled in" in (r.notes or "")


# --- recipe round trip ------------------------------------------------------

def test_a_recipe_round_trips(tmp_path=None):
    d = Path(tempfile.mkdtemp())
    r = a_recipe()
    back = recipe_mod.Recipe.load(r.save(d / "r.json"))
    assert back == r


def test_a_recipe_from_a_future_schema_version_is_refused():
    d = Path(tempfile.mkdtemp())
    p = d / "r.json"
    raw = json.loads(json.dumps(a_recipe().__dict__))
    raw["schema_version"] = 99
    p.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="schema version"):
        recipe_mod.Recipe.load(p)


# --- bundle fingerprint -----------------------------------------------------

def test_the_fingerprint_covers_what_decides_generation():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    fp = recipe_mod.bundle_fingerprint(d)
    assert set(fp["files"]) == {"concepts.json", "formMappings.json", "forms/"}
    assert fp["combined"]


def test_a_changed_form_changes_the_fingerprint():
    a, b = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    fixture.write(a); fixture.write(b)
    before = recipe_mod.bundle_fingerprint(b)["combined"]
    (b / "forms" / "form.json").write_text(
        (b / "forms" / "form.json").read_text().replace("Test Form", "Edited Form"))
    assert recipe_mod.bundle_fingerprint(b)["combined"] != before
    assert recipe_mod.bundle_fingerprint(a)["combined"] == before


def test_an_unrelated_bundle_file_does_not_change_the_fingerprint():
    """Hashing the whole directory would make a dashboard or translation edit look like a change
    to the dataset."""
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    before = recipe_mod.bundle_fingerprint(d)["combined"]
    (d / "reportDashboard.json").write_text('[{"unrelated": true}]')
    assert recipe_mod.bundle_fingerprint(d)["combined"] == before


def test_check_bundle_reports_a_substituted_bundle():
    d = Path(tempfile.mkdtemp())
    fixture.write(d)
    r = a_recipe()
    r.bundle_fingerprint = recipe_mod.bundle_fingerprint(d)
    assert r.check_bundle(d) == []
    (d / "concepts.json").write_text("[]")
    problems = r.check_bundle(d)
    assert problems and "will not be the same" in problems[0]


def test_check_bundle_says_so_when_it_cannot_check():
    assert "cannot be checked" in a_recipe().check_bundle("/tmp")[0]


# --- manifest ---------------------------------------------------------------

def manifest_for(counts, contents=None):
    d = Path(tempfile.mkdtemp())
    for table, n in counts.items():
        (d / f"{table}.tsv").write_text((contents or "row\n") * n)
    return recipe_mod.Manifest.of("test", d, counts)


def test_a_manifest_records_rows_bytes_and_a_hash():
    m = manifest_for({"individual": 3})
    e = m.tables["individual"]
    assert e["rows"] == 3 and e["bytes"] > 0 and len(e["sha256"]) == 64
    assert m.total_rows == 3


def test_a_manifest_records_the_generator_commit():
    m = manifest_for({"individual": 1})
    assert "generator_commit" in m.provenance and "generator_dirty" in m.provenance


def test_an_identical_rebuild_shows_no_differences():
    a = manifest_for({"individual": 3})
    b = manifest_for({"individual": 3})
    assert a.differences(b) == []


def test_a_changed_row_count_is_reported():
    a, b = manifest_for({"individual": 3}), manifest_for({"individual": 2})
    assert a.differences(b) == ["individual: 3 rows against 2"]


def test_the_same_row_count_with_different_content_is_reported():
    """Row counts alone would miss most changes to the generator."""
    a = manifest_for({"individual": 3}, contents="a\n")
    b = manifest_for({"individual": 3}, contents="b\n")
    assert a.differences(b) == ["individual: same row count, different content"]


def test_a_manifest_round_trips():
    d = Path(tempfile.mkdtemp())
    m = manifest_for({"individual": 2})
    assert recipe_mod.Manifest.load(m.save(d / "m.json")).tables == m.tables


# --- verdict ----------------------------------------------------------------

def observed(gin_per_row=69):
    rows = 1_000_000
    return {"program_encounter": {"rows": rows, "gin_observation_bytes": gin_per_row * rows,
                                  "all_index_bytes": 1722 * rows, "obs_keys_p50": 12,
                                  "obs_keys_p95": 34, "obs_mean_bytes": 879}}


def test_a_verdict_records_the_gate_result_and_what_it_judged_against():
    p = profile_mod.load()
    doc = recipe_mod.verdict_document("pilot-day-180", validate.run(observed(), p))
    assert doc["verdict"] == "pass"
    assert doc["recipe"] == "pilot-day-180" and doc["profile"] == p.name
    assert doc["counts"]["failed"] == 0 and doc["checks"]


def test_a_failing_dataset_records_a_failing_verdict():
    doc = recipe_mod.verdict_document("bad", validate.run(observed(gin_per_row=7),
                                                          profile_mod.load()))
    assert doc["verdict"] == "fail"
    assert any(c["verdict"] == "fail" and c["name"] == "GIN bytes/row" for c in doc["checks"])


# --- a bundle per tenant ----------------------------------------------------

def test_bundle_paths_fall_back_to_the_deployments():
    r = a_recipe()
    paths = r.bundle_paths()
    assert set(paths) == {t["organisation_id"] for t in r.tenants}
    assert set(paths.values()) == {"/tmp/bundle"}


def test_a_tenant_can_name_its_own_bundle():
    r = a_recipe()
    r.tenants[0]["bundle_path"] = "/tmp/large-config"
    paths = r.bundle_paths()
    assert paths[r.tenants[0]["organisation_id"]] == "/tmp/large-config"
    assert paths[r.tenants[1]["organisation_id"]] == "/tmp/bundle"


def test_per_tenant_bundles_are_fingerprinted_and_checked():
    a, b = Path(tempfile.mkdtemp()), Path(tempfile.mkdtemp())
    fixture.write(a); fixture.write(b)
    r = a_recipe()
    r.bundle_path = str(a)
    r.tenants[1]["bundle_path"] = str(b)
    r.fingerprint_tenants()
    assert len(r.tenant_bundle_fingerprints) == len(r.tenants)
    assert r.check_tenant_bundles() == []
    (b / "concepts.json").write_text("[]")
    problems = r.check_tenant_bundles()
    assert len(problems) == 1
    assert str(r.tenants[1]["organisation_id"]) in problems[0]


def test_the_committed_recipes_allow_a_bundle_per_tenant():
    """H1: cover the range of organisation size deliberately rather than assuming the small case
    generalises. Config size drives the syncDetails row count."""
    r = recipe_mod.Recipe.load(DATASETS / "pilot-day-180.json")
    assert all("bundle_path" in t for t in r.tenants)
    assert "own bundle_path" in (r.notes or "")


def test_a_recipe_captures_every_tenant_field():
    """A recipe promises the dataset can be rebuilt exactly, so it has to carry every input.

    This is the guard on that promise. The tenant dict used to be hand-written and had fallen two
    fields behind -- workers_per_supervisor, which sets a tenant's supervisor count and catchment
    width, and total_encounters, which sizes every co-tenant. TenantSpec fills absent fields with
    defaults, so a recipe missing one rebuilds a *different* dataset without raising.
    """
    import dataclasses

    spec = dep.TenantSpec(name="state-1", organisation_id=1, field_workers=500,
                          workers_per_supervisor=20, total_encounters=12345)
    deployment = dep.DeploymentSpec(tenants=(spec,), days=180, reference=date(2026, 3, 1))
    r = recipe_mod.Recipe.from_deployment("t", deployment, profile="p", bundle_path=".", bundle_revision="rev")

    captured = set(r.tenants[0])
    declared = {f.name for f in dataclasses.fields(dep.TenantSpec)}
    assert declared <= captured, f"recipe drops {sorted(declared - captured)}"


def test_a_tenant_round_trips_through_a_recipe_unchanged():
    """Rebuilt from its own recipe, a tenant must be the tenant that was written down."""

    spec = dep.TenantSpec(name="state-1", organisation_id=1, field_workers=500,
                          workers_per_supervisor=20)
    deployment = dep.DeploymentSpec(tenants=(spec,), days=180, reference=date(2026, 3, 1))
    r = recipe_mod.Recipe.from_deployment("t", deployment, profile="p", bundle_path=".", bundle_revision="rev")

    rebuilt = r.to_deployment().tenants[0]
    assert rebuilt == spec

    # And the span actually survives into the tree, which is the thing that would differ.
    import catchments as cat
    supervisors = lambda t: len([c for c in dep.build_tenant(t, 0).catchments
                                 if c.role == cat.SUPERVISOR])
    assert supervisors(rebuilt) == supervisors(spec) == 25
