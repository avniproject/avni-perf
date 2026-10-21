"""compare-trajectory.py must pick the customers whether or not co-tenants are running."""
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "ct", Path(__file__).resolve().parents[1] / "compare-trajectory.py")
ct = importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(ct)
BAR = "=" * 80


def block(elapsed, scenarios, requests, ko=0):
    body = f"\n{elapsed}s elapsed\n"
    for name, (a, d) in scenarios:
        body += f"---- {name} ----------\n[|   ]  0%\n          waiting: 9 / active: {a} / done: {d}\n"
    body += f"---- Requests ----\n> Global | {requests:,} | {requests - ko:,} | {ko} |\n"
    return body + BAR


def test_with_co_tenants_the_customer_line_is_the_one_taken(tmp_path):
    p = tmp_path / "a.log"
    p.write_text(block(300, [("Co-tenant", (43, 91)), ("Customer", (137, 146))], 7409))
    assert ct.parse(p)[1] == (300, (137, 146), 7409, 0)


def test_without_co_tenants_the_single_scenario_is_the_customers(tmp_path):
    p = tmp_path / "b.log"
    p.write_text(block(600, [("Sync realistic", (37, 1132))], 23335))
    assert ct.parse(p)[2] == (600, (37, 1132), 23335, 0)


def test_two_unnamed_scenarios_are_not_guessed_between(tmp_path):
    p = tmp_path / "c.log"
    p.write_text(block(300, [("Alpha", (1, 1)), ("Beta", (2, 2))], 10))
    assert ct.parse(p) == {}
