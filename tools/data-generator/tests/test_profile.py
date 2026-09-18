import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

import profile as profile_mod


def write(d: dict) -> str:
    p = Path(tempfile.mkdtemp()) / "p.json"
    p.write_text(json.dumps(d))
    return str(p)


def test_default_profile_carries_every_measured_form_type():
    p = profile_mod.load()
    assert set(p.targets) == {"IndividualProfile", "ProgramEnrolment", "ProgramEncounter", "Encounter"}
    assert p.name == "production-2026-09"


def test_default_profile_matches_the_measured_values():
    """These are Q6's output. A change here should be a re-measurement, not a nudge."""
    t = profile_mod.load().targets
    assert (t["ProgramEncounter"].key_count.p50, t["ProgramEncounter"].key_count.p95) == (12, 34)
    assert (t["Individual" "Profile"].key_count.p50, t["IndividualProfile"].key_count.p95) == (7, 29)
    assert (t["Encounter"].key_count.p50, t["Encounter"].key_count.p95) == (4, 22)
    assert (t["ProgramEnrolment"].key_count.p50, t["ProgramEnrolment"].key_count.p95) == (2, 20)


def test_a_run_can_target_something_other_than_production():
    p = profile_mod.load(write({"name": "heavier", "form_types": {
        "ProgramEncounter": {"table": "program_encounter", "p50_keys": 40, "p95_keys": 120}}}))
    assert p.name == "heavier"
    assert p.targets["ProgramEncounter"].key_count.p95 == 120


def test_missing_percentile_is_rejected():
    with pytest.raises(ValueError, match="p95_keys"):
        profile_mod.load(write({"form_types": {"Encounter": {"p50_keys": 4}}}))


def test_profile_without_form_types_is_rejected():
    with pytest.raises(ValueError, match="form_types"):
        profile_mod.load(write({"name": "empty"}))


def test_missing_file_is_reported():
    with pytest.raises(FileNotFoundError):
        profile_mod.load("/nonexistent/profile.json")


def test_an_invalid_distribution_is_caught_at_load():
    with pytest.raises(ValueError):
        profile_mod.load(write({"form_types": {
            "Encounter": {"p50_keys": 30, "p95_keys": 4}}}))


def test_catchment_volumes_reproduce_q3():
    c = profile_mod.load().catchment
    assert set(c) == {"subjects", "enrolments", "program_encounters", "encounters"}
    assert c["program_encounters"].quantile(0.99) == pytest.approx(153126)
    assert c["subjects"].quantile(0.5) == pytest.approx(464)


def test_the_catchment_note_is_not_read_as_an_entity():
    assert "note" not in profile_mod.load().catchment


def test_temporal_spread_is_reported_as_a_guess():
    """H3 says getting this wrong invalidates every incremental scenario. Q14 is not yet run."""
    p = profile_mod.load()
    assert p.temporal is not None and p.temporal.unmeasured
    assert p.unmeasured_inputs == ["temporal_spread"]


def test_a_measured_temporal_spread_stops_being_reported():
    p = profile_mod.load(write({"form_types": {"Encounter": {"p50_keys": 4, "p95_keys": 22}},
                                "temporal_spread": {"days_p50": 30, "days_p99": 900,
                                                    "edited_after_creation_fraction": 0.2}}))
    assert p.temporal.unmeasured is False
    assert p.unmeasured_inputs == []


def test_a_profile_may_omit_catchment_and_temporal():
    p = profile_mod.load(write({"form_types": {"Encounter": {"p50_keys": 4, "p95_keys": 22}}}))
    assert p.catchment == {} and p.temporal is None
