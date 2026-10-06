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


# --- the two supervisor spans split to the same names ------------------------

FIELDS = ["userName", "lastModifiedDateTime", "password|token", "pushScale", "deviceId",
          "role", "organisationUUID"]


def _write_users(path, supervisors_per_tenant, tenants=10, workers_per_tenant=5):
    """A ten-tenant pilot, differing from another only in how many supervisors it has -- which is
    exactly how the two spans differ."""
    rows = []
    for t in range(10, 10 + tenants):
        for i in range(workers_per_tenant):
            rows.append(dict.fromkeys(FIELDS, ""))
            rows[-1].update(userName=f"w{t}-{i}", role="field_worker", organisationUUID=f"org-{t}")
        for i in range(supervisors_per_tenant):
            rows.append(dict.fromkeys(FIELDS, ""))
            rows[-1].update(userName=f"s{t}-{i}", role="supervisor", organisationUUID=f"org-{t}")
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path


def test_a_variant_suffixes_every_slice():
    """Block A' repeats cases 3 to 5 on the span-20 dataset. Both are ten-tenant pilots, so
    without a suffix both split to the same four names."""
    rows = [{"organisationUUID": f"org-{o}", "role": "supervisor"} for o in range(10, 20)]
    assert list(sf.slices(rows, "span20")) == [
        "case2-users-span20.csv", "case3-users-span20.csv",
        "case4-users-span20.csv", "case5-users-span20.csv"]
    assert list(sf.slices(rows)) == [
        "case2-users.csv", "case3-users.csv", "case4-users.csv", "case5-users.csv"]


def test_splitting_a_second_dataset_over_the_first_is_refused(tmp_path, capsys):
    """**This is the failure the flag exists for.** Case 3 is 60 users at span 8.4 and 25 at span
    20. Silently replaced, a run drives 25 users, completes, and reports as the measured point."""
    _write_users(tmp_path / "a.csv", supervisors_per_tenant=6)
    assert sf.main([str(tmp_path / "a.csv")]) == 0
    before = (tmp_path / "case3-users.csv").read_bytes()

    _write_users(tmp_path / "b.csv", supervisors_per_tenant=2)
    assert sf.main([str(tmp_path / "b.csv")]) == 2
    assert (tmp_path / "case3-users.csv").read_bytes() == before, (
        "a refused split must leave every slice as it was")
    err = capsys.readouterr().err
    assert "--variant" in err and "case3-users.csv" in err


def test_the_refusal_is_about_contents_not_existence(tmp_path):
    """Re-splitting the same input is how someone checks what a dataset holds. Refusing that
    would make the check a nuisance and the flag something to work around."""
    _write_users(tmp_path / "a.csv", supervisors_per_tenant=6)
    assert sf.main([str(tmp_path / "a.csv")]) == 0
    assert sf.main([str(tmp_path / "a.csv")]) == 0


def test_a_variant_and_force_both_get_past_it(tmp_path):
    _write_users(tmp_path / "a.csv", supervisors_per_tenant=6)
    sf.main([str(tmp_path / "a.csv")])
    _write_users(tmp_path / "b.csv", supervisors_per_tenant=2)

    assert sf.main([str(tmp_path / "b.csv"), "--variant", "span20"]) == 0
    with (tmp_path / "case3-users-span20.csv").open() as fh:
        assert len(list(csv.DictReader(fh))) == 2
    with (tmp_path / "case3-users.csv").open() as fh:
        assert len(list(csv.DictReader(fh))) == 6, "the first split must be untouched"

    assert sf.main([str(tmp_path / "b.csv"), "--force"]) == 0
    with (tmp_path / "case3-users.csv").open() as fh:
        assert len(list(csv.DictReader(fh))) == 2


def test_a_variant_that_is_not_a_file_name_fragment_is_refused(tmp_path):
    """The label lands in a path, so it cannot be anything that is not a name. A label argparse
    reads as an option of its own (`-leading`) fails there instead, which is the same exit code
    and the same outcome -- nothing written."""
    _write_users(tmp_path / "a.csv", supervisors_per_tenant=6)
    for bad in ("../escape", "Span20", "span 20", "", "-leading"):
        try:
            code = sf.main([str(tmp_path / "a.csv"), "--variant", bad])
        except SystemExit as exit:
            code = exit.code
        assert code == 2, bad
    assert not list(tmp_path.glob("case*"))
