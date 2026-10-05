"""The committed user files, and the one thing that must never be true of them."""
import csv
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
RESOURCES = ROOT / "src/gatling/resources"
_spec = importlib.util.spec_from_file_location("sf", ROOT / "tools/scenario-feeders.py")
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)


def _tracked_feeders():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "src/gatling/resources/*-users.csv"],
                         capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out]


def test_no_committed_feeder_carries_a_credential():
    """**The reason these are committed at all is that they cannot leak anything.** They are
    generated usernames against generated organisations, with an empty `password|token`. A feeder
    built under AUTH_MODE=cognito carries real tokens in that column, and the .gitignore is
    default-deny so one cannot arrive here without someone un-ignoring it. This is the check that
    makes that deliberate rather than hopeful."""
    feeders = _tracked_feeders()
    assert feeders, "no user files are tracked; this test is guarding nothing"
    for path in feeders:
        with path.open() as fh:
            for i, row in enumerate(csv.DictReader(fh), start=2):
                assert not row.get("password|token"), (
                    f"{path.name} line {i} carries a credential; it must not be committed")


def test_every_committed_feeder_has_the_columns_the_simulation_reads():
    """The simulation reads userName, lastModifiedDateTime, password|token and pushScale, and
    resolves per-tenant media and concentration from organisationUUID."""
    for path in _tracked_feeders():
        with path.open() as fh:
            fields = csv.DictReader(fh).fieldnames or []
        for column in ("userName", "lastModifiedDateTime", "password|token", "pushScale"):
            assert column in fields, f"{path.name} is missing {column}"


def test_the_slices_are_one_tenant_because_the_cases_are():
    """Cases 2, 3 and 4 are each *one state tenant*. The generated file spans every tenant in the
    deployment, so pointing a run at it drives a case that is not in the plan -- the run completes
    and the number belongs to nothing."""
    rows = [{"organisationUUID": "org-10", "role": "field_worker"},
            {"organisationUUID": "org-10", "role": "supervisor"},
            {"organisationUUID": "org-11", "role": "field_worker"}]
    out = sf.slices(rows)
    for name, subset in out.items():
        assert {r["organisationUUID"] for r in subset} == {"org-10"}, name
    assert [r["role"] for r in out["case2-users.csv"]] == ["field_worker"]
    assert [r["role"] for r in out["case3-users.csv"]] == ["supervisor"]
    assert len(out["case4-users.csv"]) == 2


def test_case5_is_not_written_from_a_two_tenant_file():
    """A two-tenant file named case5-users.csv is the same trap one layer down."""
    two = [{"organisationUUID": f"org-{o}", "role": "field_worker"} for o in (10, 11)]
    assert "case5-users.csv" not in sf.slices(two)
    ten = [{"organisationUUID": f"org-{o}", "role": "field_worker"} for o in range(1, 11)]
    assert "case5-users.csv" in sf.slices(ten)
