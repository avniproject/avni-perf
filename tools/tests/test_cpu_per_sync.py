"""Spreading a run's CPU across its syncs.

There is no per-sync CPU measurement -- the metric is whole-server -- so the percentiles rest
entirely on the weighting. These test that the weighting is what it claims, that the full and
incremental split is by the flag rather than by size, and that the cohort split does not silently
average a co-tenant sync against a customer one.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("cps", ROOT / "tools/cpu-per-sync.py")
cps = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cps)


def row(user="state-1-u1", records=1000, server_ms=100.0, full=False):
    return {"user": user, "records": float(records), "serverMs": server_ms, "full": full}


def test_cpu_is_shared_in_proportion_to_server_time():
    # 300 CPU seconds over syncs that asked for 100, 200 and 300 ms of server.
    d = cps.distribute(300.0, [row(server_ms=100), row(server_ms=200), row(server_ms=300)])
    assert d["weightedBy"] == "serverMs"
    assert d["all"]["n"] == 3
    assert round(d["all"]["mean"], 2) == 100.0          # the total still divides by the count
    assert d["all"]["p50"] == 100.0                     # 300 x 200/600


def test_records_are_the_fallback_when_server_time_is_absent():
    d = cps.distribute(100.0, [row(server_ms=0, records=1), row(server_ms=0, records=3)])
    assert d["weightedBy"] == "records"
    assert d["all"]["p50"] == 25.0                      # 100 x 1/4


def test_full_and_incremental_are_split_by_the_flag_not_by_size():
    # A small full sync and a large incremental one: the split must follow fullSync.
    rows = [row(server_ms=10, full=True), row(server_ms=990, full=False)]
    d = cps.distribute(1000.0, rows)
    assert d["full"]["n"] == 1 and d["incremental"]["n"] == 1
    assert d["full"]["p50"] == 10.0
    assert d["incremental"]["p50"] == 990.0


def test_a_run_with_no_full_syncs_reports_none_rather_than_zero():
    d = cps.distribute(100.0, [row(), row()])
    assert d["full"] is None, "an absent category must not read as a measured zero"
    assert d["incremental"]["n"] == 2


def test_co_tenant_syncs_are_separated_from_customer_ones():
    # The failure this prevents: case 7 reads 2.01 CPU/sync only because 1,584 of its 1,864
    # syncs are small co-tenant ones averaged against 280 large customer ones.
    rows = [row(user="state-1-u1", server_ms=900)] + [row(user="co-001-u9", server_ms=25)] * 4
    d = cps.distribute(1000.0, rows)
    assert d["customer"]["n"] == 1 and d["coTenant"]["n"] == 4
    assert d["customer"]["p50"] == 900.0
    assert d["coTenant"]["p50"] == 25.0


def test_no_cohort_keys_when_every_sync_is_the_customer():
    d = cps.distribute(10.0, [row(), row()])
    assert "customer" not in d and "coTenant" not in d


def test_a_run_with_no_weight_at_all_yields_nothing():
    assert cps.distribute(10.0, [row(server_ms=0, records=0)]) is None
