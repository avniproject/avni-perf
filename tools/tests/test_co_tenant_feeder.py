"""The checks that stand between a generated feeder and a run that looks fine and measures the
wrong thing."""
import csv
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cof", ROOT / "tools/co-tenant-feeder.py")
cof = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cof)

FIELDS = ["userName", "lastModifiedDateTime", "password|token", "pushScale", "organisationUUID"]


def _write(path, rows):
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    return path


def _row(org, i, token=""):
    return {"userName": f"co-{org}-u{i}", "lastModifiedDateTime": "1900-01-01T00:00:00.000Z",
            "password|token": token, "pushScale": "1.0", "organisationUUID": f"org-{org}"}


def test_a_generated_feeder_passes(tmp_path):
    rows = [_row(1000 + o, i) for o in range(1, 21) for i in range(o)]
    problems, got, orgs = cof.check(_write(tmp_path / "sync-users.csv", rows))
    assert problems == []
    assert len(orgs) == 20


def test_a_feeder_without_organisation_uuid_is_refused(tmp_path):
    """**The failure this exists for.** Without the column every row collapses into one
    organisation, every draw takes rank 1, and the run reproduces production's request rate with a
    single-tenant working set -- which is the opposite of what cases 7 and 13 measure, at the right
    rate, with an ordinary-looking report."""
    path = tmp_path / "sync-users.csv"
    rows = [_row(1001, i) for i in range(10)]
    with path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[f for f in FIELDS if f != "organisationUUID"])
        w.writeheader()
        w.writerows([{k: v for k, v in r.items() if k != "organisationUUID"} for r in rows])
    problems, _, _ = cof.check(path)
    assert any("organisationUUID" in p for p in problems)


def test_a_single_tenant_feeder_is_refused(tmp_path):
    """The column can be present and still useless: one organisation draws uniformly."""
    rows = [_row(1001, i) for i in range(50)]
    problems, _, _ = cof.check(_write(tmp_path / "sync-users.csv", rows))
    assert any("organisation(s)" in p for p in problems)


def test_credentials_are_refused(tmp_path):
    """Same bar as the case feeders: a token in the file is a token in anyone's checkout."""
    rows = [_row(1000 + o, 0) for o in range(1, 5)]
    rows[2]["password|token"] = "eyJhbGciOi"
    problems, _, _ = cof.check(_write(tmp_path / "sync-users.csv", rows))
    assert any("credential" in p for p in problems)


def test_the_committed_example_would_not_pass_as_a_feeder(tmp_path):
    """co-tenant-users-example.csv is an example, not a cohort, and the stub beside it is
    gitignored. Neither is a feeder, and the check has to say so rather than copy one into place."""
    problems, _, _ = cof.check(ROOT / "src/gatling/resources/co-tenant-users-example.csv")
    assert problems, "the example file passes the feeder check, so the check guards nothing"
