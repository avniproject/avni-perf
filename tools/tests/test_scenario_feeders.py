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


def _allowed_by_gitignore():
    """**The .gitignore allow-list is the list these tests must cover.** `src/gatling/resources` is
    default-deny precisely so that un-ignoring a feeder is a deliberate act; this reads the same
    lines, so a file cannot become committable without also becoming checked."""
    allowed = []
    for line in (ROOT / ".gitignore").read_text().splitlines():
        line = line.strip()
        if line.startswith("!/src/gatling/resources/") and line.endswith(".csv"):
            allowed.append(ROOT / line[2:])
    return allowed


def _tracked_feeders():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "src/gatling/resources/*.csv"],
                         capture_output=True, text=True).stdout.split()
    return [ROOT / p for p in out]


def test_every_feeder_git_will_accept_is_one_these_tests_check():
    """**The glob is the whole guard, and a rename can walk out from under it.** These files were
    `caseN-users.csv` and matched `*-users.csv`; naming them for their dataset made them
    `caseN-users-pilot.csv`, which does not, and the sweep below silently went from five files to
    two while still passing. Checking the allow-list against what is tracked is the version of
    this that a rename cannot quietly shrink."""
    tracked = {p.resolve() for p in _tracked_feeders()}
    missing = [p.name for p in _allowed_by_gitignore() if p.resolve() not in tracked]
    assert not missing, f"un-ignored but not tracked, so nothing checks them: {missing}"
    # The `-example` files are templates rather than cohorts, and the deny pattern
    # (`*-users.csv`) never covered them, so they are tracked without an allow-list line. They are
    # still swept for credentials below -- an example carrying a real token would be worse, not
    # better, for being an example.
    allowed = {a.resolve() for a in _allowed_by_gitignore()}
    unlisted = [p.name for p in tracked
                if p.resolve() not in allowed and not p.name.endswith("-example.csv")]
    assert not unlisted, (
        f"tracked without an allow-list line: {unlisted}. Either un-ignore it deliberately, "
        f"after looking at the password|token column, or it should not be committed")


def test_no_committed_feeder_carries_a_credential():
    """**The reason these are committed at all is that they cannot leak anything.** They are
    generated usernames against generated organisations, with an empty `password|token`. A feeder
    built under AUTH_MODE=cognito carries real tokens in that column, and the .gitignore is
    default-deny so one cannot arrive here without someone un-ignoring it. This is the check that
    makes that deliberate rather than hopeful."""
    feeders = _tracked_feeders()
    assert len(feeders) >= 12, (
        f"only {len(feeders)} user files are swept; the glob has drifted off them again")
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


# --- a run consumes a prefix, not the file ----------------------------------

def _mixed(tenants=10, workers=50, supervisors=6):
    """Blocked the way generate.py emits: tenant by tenant, role by role."""
    rows = []
    for t in range(10, 10 + tenants):
        rows += [{"organisationUUID": f"org-{t}", "role": "field_worker"} for _ in range(workers)]
        rows += [{"organisationUUID": f"org-{t}", "role": "supervisor"} for _ in range(supervisors)]
    return rows


def test_any_prefix_carries_every_tenant_and_role_in_proportion():
    """**This is the whole point of the ordering.** `circular()` walks the file in order, so a run
    performing fewer syncs than the feeder has rows reaches only a prefix of it.

    **The guarantee is asymptotic, and it has to be.** Each row sits at (k + 0.5) / n within its
    own stratum, so a stratum of 6 members in a 560-row file appears about every 93 rows. A
    20-row prefix cannot hold 2.1 of them whatever the ordering does -- the smallest prefix that
    can represent a stratum is the spacing between its members. The cases draw 94 syncs and up,
    which is comfortably past that, so the test asserts over the range that is real rather than a
    bound no ordering could meet.
    """
    out = sf.interleave(_mixed())
    total_sup = sum(1 for r in out if r["role"] == "supervisor")
    # One stratum contributes at most one row of rounding error, and the supervisors here are ten
    # strata -- one per tenant. That is the bound; in practice it comes in far under, which the
    # committed-feeder test below pins at the prefixes the cases actually draw.
    strata = len({r["organisationUUID"] for r in out})
    for n in (94, 187, 281, 400):
        head = out[:n]
        sup = sum(1 for r in head if r["role"] == "supervisor")
        expected = n * total_sup / len(out)
        assert abs(sup - expected) <= strata, (
            f"prefix {n}: {sup} supervisors, expected ~{expected:.1f}")
        assert len({r["organisationUUID"] for r in head}) == 10, (
            f"prefix {n} does not reach all ten tenants")


def test_the_case_4_and_case_5_regressions_specifically():
    """**Case 4 measured case 2 and nobody could see it from the result.** 187 syncs against 501
    field workers followed by 60 supervisors never reached row 502, so "one state tenant, both"
    returned 60.8 s and 10,838 records against case 2's 60.8 s and 10,831. Case 5 would have been
    worse: 281 syncs against a file opening with 561 rows of one tenant, for the ten-tenant
    separate-hosting baseline that cases 6 and 7 are read against."""
    rows = _mixed()
    sliced = sf.slices(rows)

    case4 = sliced["case4-users.csv"][:187]
    assert any(r["role"] == "supervisor" for r in case4), (
        "case 4's first 187 syncs are still field workers only")

    case5 = sliced["case5-users.csv"][:281]
    assert len({r["organisationUUID"] for r in case5}) == 10, (
        "case 5's first 281 syncs do not span all ten tenants")
    assert any(r["role"] == "supervisor" for r in case5)


def test_a_single_stratum_slice_is_left_alone():
    """Cases 2, 3 and 14 draw one role from one tenant. There is nothing to interleave, and the
    order must not be churned for the sake of it -- these files are committed and diffed."""
    one = [{"organisationUUID": "org-10", "role": "field_worker", "userName": f"u{i}"}
           for i in range(50)]
    assert sf.interleave(one) == one


def test_the_order_is_deterministic():
    """Shuffling would also give a representative prefix, in expectation, and was rejected for
    exactly this: cases 5, 6 and 7 are read as deltas, so the same cohort has to sync in each."""
    rows = _mixed()
    assert sf.interleave(rows) == sf.interleave(rows)
    assert [r["userName"] for r in sf.interleave(_write_named(rows))] == \
           [r["userName"] for r in sf.interleave(_write_named(rows))]


def _write_named(rows):
    return [dict(r, userName=f"u{i}") for i, r in enumerate(rows)]


def test_the_committed_feeders_are_interleaved():
    """The property has to hold in the files that actually run, not only in the function."""
    for name, n in (("case4-users-pilot.csv", 187), ("case5-users-pilot.csv", 281),
                    ("case4-users-span20.csv", 175)):
        path = ROOT / "src/gatling/resources" / name
        with path.open() as fh:
            rows = list(csv.DictReader(fh))
        head = rows[:n]
        assert any(r["role"] == "supervisor" for r in head), f"{name} has no supervisor in {n}"
        if len({r["organisationUUID"] for r in rows}) > 1:
            assert len({r["organisationUUID"] for r in head}) == \
                   len({r["organisationUUID"] for r in rows}), f"{name} misses tenants in {n}"
        # Tight here, where the prefix is the one the case really draws: 20 of 20 for case 4,
        # 28 against 29 for case 5.
        sup = sum(1 for r in head if r["role"] == "supervisor")
        expected = n * sum(1 for r in rows if r["role"] == "supervisor") / len(rows)
        assert abs(sup - expected) <= 2, (
            f"{name} prefix {n}: {sup} supervisors, expected ~{expected:.1f}")
