"""The run log's two concurrency columns, which have now been wrong three times.

`update-run-log.sh` is a bash wrapper around one python heredoc, so the function under test is
read out of the script's own source rather than imported. That keeps the test on the real code
without restructuring a script whose shape is deliberate -- it has to run on an injector with
nothing but bash, python3 and the AWS CLI.
"""
import re
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "tools/update-run-log.sh"


def _load(name):
    src = SCRIPT.read_text()
    m = re.search(rf"^def {name}\(.*?(?=^def |\Z)", src, re.S | re.M)
    assert m, f"{name} is not defined in {SCRIPT.name} any more"
    ns = {}
    exec(m.group(0), ns)
    return ns[name]


devices_in_flight = _load("devices_in_flight")


def test_the_arrival_rate_is_the_syncs_that_happened():
    """**Case 2 configures 500 users and performs 167 syncs**, because `steady` derives its rate
    from SYNC_WINDOW_HOURS and the run is four hours of a twelve-hour window. Using the cohort as
    the arrival count overstated the column by users/n -- 3x here."""
    case2 = devices_in_flight({"n": 167, "mean": 61.0}, wall=14400, users_n=500)
    assert round(case2, 1) == 0.7, case2
    case14 = devices_in_flight({"n": 63, "mean": 80.1}, wall=5400, users_n=501)
    assert round(case14, 1) == 0.9, case14


def test_it_agrees_with_rescaling_the_banner():
    """The banner computes the same quantity from the arrival rate and an assumed 14.1 s median.
    Correcting only its service time must land on the same number -- that the two disagreed by 3x
    is what exposed the defect, so it is the check worth keeping."""
    banner_at_14_1 = 167 / 14400 * 14.1
    rescaled = banner_at_14_1 * (61.0 / 14.1)
    measured = devices_in_flight({"n": 167, "mean": 61.0}, wall=14400, users_n=500)
    assert abs(rescaled - measured) < 0.01, (rescaled, measured)


def test_a_burst_run_is_unchanged_which_is_why_this_hid():
    """In `burst` the whole cohort arrives inside the window, so n == users_n and the old
    expression and the new one agree. Case 1 is burst, which is what the column was introduced
    against."""
    syncs = {"n": 100, "mean": 6.0}
    assert devices_in_flight(syncs, wall=1800, users_n=100) == 100 * 6.0 / 1800


def test_more_devices_than_exist_cannot_be_mid_sync():
    """A short wall against long syncs can push the product above the cohort; it is capped rather
    than printed, because the column is read as a count of real devices."""
    assert devices_in_flight({"n": 500, "mean": 120.0}, wall=60, users_n=500) == 500
