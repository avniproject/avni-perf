import csv, json, sys, tempfile
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
ROOT_RESOURCES = Path(__file__).resolve().parents[3] / "src/gatling/resources"


def filled(name):
    """A committed recipe with organisation ids filled in, for tests about its *shape*.

    The pilot recipes carry `organisation_id: null` and `to_deployment` refuses them, because the
    ids are assigned by the server and the placeholders they once held named live organisations.
    These tests are about beneficiaries, encounters and tenant counts, none of which depend on
    which organisation a tenant lands in -- so they fill arbitrary ids rather than relax the
    refusal, which is the thing being protected.
    """
    d = json.loads((DATASETS / name).read_text())
    for i, t in enumerate(d["tenants"]):
        if t.get("organisation_id") is None:
            t["organisation_id"] = 9000 + i
    f = Path(tempfile.mkdtemp()) / name
    f.write_text(json.dumps(d))
    return recipe_mod.Recipe.load(f)



def a_recipe(**kw):
    d = dep.pilot_deployment(180, REFERENCE)
    return recipe_mod.Recipe.from_deployment(
        "test", d, profile="production-2026-09", bundle_path="/tmp/bundle", **kw)


# --- the committed recipes --------------------------------------------------

@pytest.mark.parametrize("days", [60, 120, 180, 365])
def test_a_committed_recipe_rebuilds_the_deployment_it_describes(days):
    r = filled(f"pilot-day-{days}.json")
    d = r.to_deployment()
    reference = dep.pilot_deployment(days, date.fromisoformat(r.reference_date))
    assert d.beneficiaries == reference.beneficiaries
    assert d.encounters == reference.encounters
    assert len(d.tenants) == len(reference.tenants)


def test_the_committed_recipes_differ_only_in_growth_point():
    """Only encounter volume grows between the growth points."""
    rs = {d: filled(f"pilot-day-{d}.json") for d in (60, 120, 180, 365)}
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


def test_generation_refuses_early_when_the_metadata_is_not_loaded():
    """Encounter types come from the bundle, and nothing downstream guards their absence.

    `rows.py` indexes `ctx.encounter_types` directly, so an empty list fails with an IndexError
    deep inside generation rather than at the point the cause is visible. Subject types were
    already checked; encounter types were not, and a real environment with no bundle loaded is
    exactly the case that finds it.

    Programmes are deliberately absent from this check: `rows.py` guards them, and with the
    programme design out of scope a deployment with none is the expected shape.
    """
    import json
    import tempfile
    from pathlib import Path as P
    import generate

    refs = P(tempfile.mkdtemp()) / "refs.json"
    refs.write_text(json.dumps({
        "subject_types": [{"id": 1, "uuid": "st", "name": "Individual", "organisation_id": 1}],
        "programs": [],
        "encounter_types": [],
        "audit_user_id": 1,
    }))
    _, missing = generate._refs(refs, {1})
    assert ("encounter type", 1) in missing
    assert ("subject type", 1) not in missing

    refs.write_text(json.dumps({
        "subject_types": [{"id": 1, "uuid": "st", "name": "Individual", "organisation_id": 1}],
        "programs": [],
        "encounter_types": [{"id": 9, "uuid": "et", "name": "Visit", "organisation_id": 1}],
        "audit_user_id": 1,
    }))
    _, missing = generate._refs(refs, {1})
    assert missing == [], "programmes absent is fine; encounter types present is enough"


def test_tenants_get_disjoint_id_ranges_through_the_generate_path():
    """`plan_ids` promises ranges that cannot collide, and the generator used to void that.

    It splits a deployment into one-tenant deployments so each can use its own metadata ids, and
    computed the base from the slice — which returns tenant zero's base every time, so every
    tenant was allocated the same range. No multi-tenant dataset has been loaded, so it would
    have surfaced as primary key violations partway through a day-180 load.
    """
    from dataclasses import replace
    from datetime import date
    import deployment as dep

    full = dep.pilot_deployment(60, date(2026, 9, 18))
    bases = dep.plan_ids(full)

    seen = []
    for spec in full.tenants:
        one = replace(full, tenants=(spec,), id_base=bases[spec.organisation_id])
        seen.append(dep.plan_ids(one)[spec.organisation_id])

    assert len(set(seen)) == len(seen), f"tenants share an id base: {seen}"
    assert seen == sorted(seen) and seen[0] == 0
    assert seen[1] - seen[0] == dep.band_width(full.tenants[0], full.days)


def test_the_per_tenant_split_keeps_every_deployment_field():
    """The split used to rebuild DeploymentSpec by hand and dropped id_base when it was added."""
    import dataclasses
    from dataclasses import replace
    from datetime import date
    import deployment as dep

    full = dep.DeploymentSpec(
        tenants=(dep.TenantSpec(name="a", organisation_id=1, field_workers=3),
                 dep.TenantSpec(name="b", organisation_id=2, field_workers=3)),
        days=60, reference=date(2026, 9, 18), seed=7, id_base=500,
        enrolment_rate=0.33, program_encounter_share=0.44)
    one = replace(full, tenants=(full.tenants[0],), id_base=0)

    for f in dataclasses.fields(dep.DeploymentSpec):
        if f.name in ("tenants", "id_base"):
            continue
        assert getattr(one, f.name) == getattr(full, f.name), f"{f.name} lost in the split"


def _refs_file(**payload):
    """A refs.json on disk, for exercising generate._refs."""
    import tempfile
    p = Path(tempfile.mkdtemp()) / "refs.json"
    base = {"subject_types": [], "programs": [], "encounter_types": [],
            "address_level_types": [], "registration_locations": [], "audit_user_id": 1}
    base.update(payload)
    p.write_text(json.dumps(base))
    return p


def _two_orgs_sharing_a_bundle(reg_entries):
    """Two organisations carrying the same bundle.

    **Their metadata uuids are identical and their ids are not.** An import creates a row per
    organisation reusing the bundle's uuid, so a uuid identifies a row within an organisation and
    nowhere else. Village is type 14 in org 10 and type 24 in org 11.
    """
    return _refs_file(
        subject_types=[{"id": 3, "uuid": "st-patient", "name": "Patient", "organisation_id": 10},
                       {"id": 7, "uuid": "st-patient", "name": "Patient", "organisation_id": 11}],
        encounter_types=[{"id": 1, "uuid": "et", "name": "Visit", "organisation_id": 10},
                         {"id": 2, "uuid": "et", "name": "Visit", "organisation_id": 11}],
        address_level_types=[{"id": 14, "uuid": "alt-village", "name": "Village",
                              "organisation_id": 10, "level": 4, "parent_id": None},
                             {"id": 24, "uuid": "alt-village", "name": "Village",
                              "organisation_id": 11, "level": 4, "parent_id": None}],
        registration_locations=reg_entries)


def test_a_registration_rule_resolves_to_its_own_organisations_type_ids():
    """The same uuid means a different row in each organisation, and the generator needs the id."""
    import generate
    refs = _two_orgs_sharing_a_bundle([
        {"organisation_id": 10, "subject_type_uuid": "st-patient",
         "location_type_uuids": ["alt-village"]},
        {"organisation_id": 11, "subject_type_uuid": "st-patient",
         "location_type_uuids": ["alt-village"]}])
    out, missing = generate._refs(refs, {10, 11})
    assert missing == []
    assert out[10][4] == [14]
    assert out[11][4] == [24]


def test_a_rule_belonging_to_another_organisation_is_not_inherited():
    """Without the organisation filter every tenant takes the union of every tenant's rules.

    Harmless while every organisation carries the same bundle, which is exactly why it would have
    gone unnoticed: the dump carried three identical entries for four organisations and no way to
    tell which one was missing a rule.
    """
    import generate
    refs = _two_orgs_sharing_a_bundle([
        {"organisation_id": 10, "subject_type_uuid": "st-patient",
         "location_type_uuids": ["alt-village"]}])
    out, _ = generate._refs(refs, {10, 11})
    assert out[10][4] == [14]
    assert out[11][4] == [], "org 11 has no rule of its own, so registration is unrestricted"


def test_an_untagged_rule_is_ignored_rather_than_applied_everywhere():
    """A dump taken before refs.sql projected organisation_id. Applying it to every tenant would
    silently truncate hierarchies nobody asked to truncate."""
    import generate
    refs = _two_orgs_sharing_a_bundle([
        {"subject_type_uuid": "st-patient", "location_type_uuids": ["alt-village"]}])
    out, _ = generate._refs(refs, {10, 11})
    assert out[10][4] == [] and out[11][4] == []


def test_a_location_type_uuid_absent_from_the_organisation_is_reported():
    """Rather than silently dropping it and generating against an untruncated hierarchy."""
    import generate
    refs = _two_orgs_sharing_a_bundle([
        {"organisation_id": 10, "subject_type_uuid": "st-patient",
         "location_type_uuids": ["alt-nowhere"]}])
    _, missing = generate._refs(refs, {10, 11})
    assert any("alt-nowhere" in str(m[0]) for m in missing)


def test_committed_recipes_claim_disjoint_id_bands():
    """Two recipes loaded into one database must not allocate the same primary keys.

    **`plan_ids` guarantees disjointness within a deployment and says nothing across
    deployments.** tanuh-small and states-day-180 were both written with id_base 1,000,000, so
    their first tenants wanted the same ids in the same database. The load fails fast --
    address_level is the first non-empty table, so it dies within seconds inside its transaction
    rather than hours in -- but the collision is only visible once someone tries.

    Recipes that leave id_base unset are skipped: they have not claimed a band, and the run that
    uses one has to choose.
    """
    import deployment as dep
    import recipe as recipe_mod

    claimed = []
    for path in sorted((Path(__file__).resolve().parents[1] / "datasets").glob("*.json")):
        if path.name.endswith(".waivers.json"):
            continue
        r = recipe_mod.Recipe.load(path)
        if not r.id_base:
            continue
        d = r.to_deployment()
        top = max(dep.plan_ids(d).values()) + dep.ID_STRIDE
        claimed.append((r.id_base, top, path.name))

    claimed.sort()
    for (lo, hi, name), (next_lo, _, next_name) in zip(claimed, claimed[1:]):
        assert hi <= next_lo, (
            f"{name} claims {lo:,}..{hi:,} and {next_name} starts at {next_lo:,}; "
            f"loading both into one database collides on the primary key")


def test_a_recipe_without_organisation_ids_refuses_to_build():
    """**The committed pilot recipes held organisation ids 1 to 10, which are not free.** On the
    load environment 1 is the platform organisation, 3 the customer's, 9 a fixture and 10 the
    first state tenant, so generating against them would have written a pilot dataset into four
    live organisations.

    `_refs` only catches that while some of the ten are missing from refs.json. Provision the
    other six and it goes through. The ids are SERIAL and assigned by the server, so a recipe
    cannot hold real ones until the tenants exist -- which means the honest state is null, and
    null has to refuse rather than default, because a default here is a guess at which
    organisation to overwrite.
    """
    import json
    import tempfile
    from pathlib import Path as P
    import recipe as recipe_mod

    src = json.loads((P(__file__).resolve().parents[1]
                      / "datasets" / "pilot-day-180.json").read_text())

    # Emptied here rather than asserted on the committed file: those ids are filled in now that
    # the ten tenants exist (6 Oct 2026), which is the state this refusal was built to reach. The
    # mechanism is what needs a test, and it has to keep working for the next recipe written
    # before its organisations are provisioned.
    blank = dict(src, tenants=[dict(t, organisation_id=None) for t in src["tenants"]])
    bf = P(tempfile.mkdtemp()) / "blank.json"
    bf.write_text(json.dumps(blank))
    r = recipe_mod.Recipe.load(bf)
    assert len(r.unassigned_organisations()) == 10
    with pytest.raises(ValueError, match="no organisation_id"):
        r.to_deployment()

    # Filled in, it builds -- and the committed one is, so it builds as it stands.
    f = P(tempfile.mkdtemp()) / "filled.json"
    f.write_text(json.dumps(src))
    filled = recipe_mod.Recipe.load(f)
    assert filled.unassigned_organisations() == []
    assert len(filled.to_deployment().tenants) == 10

    # Half-filled is the dangerous middle, and is refused too.
    half = dict(src, tenants=[dict(t, organisation_id=None if i < 5 else t["organisation_id"])
                              for i, t in enumerate(src["tenants"])])
    hf = P(tempfile.mkdtemp()) / "half.json"
    hf.write_text(json.dumps(half))
    with pytest.raises(ValueError, match="no organisation_id"):
        recipe_mod.Recipe.load(hf).to_deployment()


def test_every_committed_recipe_either_has_real_ids_or_none():
    """A half-filled recipe is the dangerous state: it would generate for the tenants that have
    ids and silently skip the question for the rest."""
    import json
    from pathlib import Path as P
    for f in sorted((P(__file__).resolve().parents[1] / "datasets").glob("*.json")):
        if "waiver" in f.name:
            continue
        tenants = json.loads(f.read_text()).get("tenants", [])
        ids = [t.get("organisation_id") for t in tenants]
        assert not ids or all(i is None for i in ids) or all(i for i in ids), \
            f"{f.name} has some tenants with organisation ids and some without: {ids[:12]}"


# --- bundle archetypes ------------------------------------------------------

def test_every_co_tenant_names_an_archetype():
    """**Config size is a load variable, so it cannot be left to a default.** The number of
    entities a config defines is the number of rows posted to syncDetails and therefore the
    per-row queries filterChangedEntities runs. A tenant with no archetype falls back to the
    deployment-wide bundle, which would build all 513 co-tenants from one config."""
    r = recipe_mod.Recipe.load(DATASETS / "co-tenants-day-180.json")
    missing = [t["name"] for t in r.tenants if not t.get("bundle_archetype")]
    assert not missing, f"{len(missing)} co-tenants have no bundle_archetype: {missing[:5]}"
    assert r.archetypes() == {"large-pull-heavy": 11, "media-heavy": 2, "push-dominated": 500}


def test_the_three_measured_ranks_keep_their_own_bundle():
    """Ranks 1, 3 and 17 are the organisations whose real bundles were obtained and whose media
    rates MediaProfiles measures. Their archetype is observed, not inferred from a threshold."""
    r = recipe_mod.Recipe.load(DATASETS / "co-tenants-day-180.json")
    by_rank = {i + 1: t["bundle_archetype"] for i, t in enumerate(r.tenants)}
    assert by_rank[1] == "large-pull-heavy"
    assert by_rank[3] == "push-dominated"
    assert by_rank[17] == "media-heavy"


def test_an_archetype_that_does_not_resolve_is_named_rather_than_ignored(tmp_path):
    """**The fallback is the dangerous path.** An unresolved archetype drops through to the
    deployment's bundle, so generation succeeds at the wrong configuration for however many
    tenants and nothing says so."""
    r = recipe_mod.Recipe.load(DATASETS / "co-tenants-day-180.json")
    assert r.unresolved_archetypes(None) == ["large-pull-heavy", "media-heavy", "push-dominated"]
    (tmp_path / "push-dominated").mkdir()
    assert r.unresolved_archetypes(tmp_path) == ["large-pull-heavy", "media-heavy"]
    for a in ("large-pull-heavy", "media-heavy"):
        (tmp_path / a).mkdir()
    assert r.unresolved_archetypes(tmp_path) == []


def test_an_archetype_resolves_under_the_root_and_an_explicit_path_still_wins(tmp_path):
    r = recipe_mod.Recipe.load(DATASETS / "co-tenants-day-180.json")
    paths = r.bundle_paths(tmp_path)
    first = r.tenants[0]["organisation_id"]
    assert paths[first] == str(tmp_path / "large-pull-heavy")

    r.tenants[0] = dict(r.tenants[0], bundle_path="/somewhere/explicit")
    assert r.bundle_paths(tmp_path)[first] == "/somewhere/explicit"


def test_a_recipe_without_archetypes_is_unaffected():
    """The pilots name no archetype, so bundle_root must change nothing for them."""
    r = recipe_mod.Recipe.load(DATASETS / "pilot-day-180.json")
    assert r.archetypes() == {}
    assert r.unresolved_archetypes(None) == []
    assert r.bundle_paths("/anywhere") == r.bundle_paths()


def test_case_8_can_reuse_case_4s_feeder_across_growth_points():
    """**Case 8 runs case 4's users against day 60, 120 and 365, and that works only by virtue of
    tenant order.** `plan_ids` walks the tenants in order, advancing a cursor by
    `band_width(tenant, days)` -- which scales with `days`. So every tenant after the first gets a
    different base at every growth point, and usernames follow the base: an NGO tenant's first
    user is `u2400001` at day 60 and `u7200001` at day 180. Only the first tenant's base is
    `id_base` regardless of days, and case 4's cohort is exactly that tenant.

    Reorder the tenants in these recipes and case 8's feeder silently names users that do not
    exist at the other growth points. Nothing else states this, so it is stated here.
    """
    bases = {}
    for days in (60, 120, 180, 365):
        d = filled(f"pilot-day-{days}.json").to_deployment()
        bases[days] = dep.plan_ids(d)

    first = filled("pilot-day-180.json").to_deployment().tenants[0]
    assert first.name == "state-1", (
        "case 4 and case 8 are the first tenant; if that is no longer state-1 the feeders are "
        "naming a different cohort")
    assert len({b[first.organisation_id] for b in bases.values()}) == 1, (
        "the first tenant's id base moved between growth points, so case 8 cannot reuse case 4's "
        "feeder")

    # And every other tenant does move, which is why only case 4's cohort is reusable.
    others = [t.organisation_id for t in
              filled("pilot-day-180.json").to_deployment().tenants[1:]]
    moved = [o for o in others if len({b[o] for b in bases.values()}) > 1]
    assert moved == others, (
        "some later tenant's base is stable across growth points; the reasoning above, and "
        "case 5's exclusion from case 8, assume none of them are")
