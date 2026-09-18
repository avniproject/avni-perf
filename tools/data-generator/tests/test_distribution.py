import random, statistics, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from distribution import Quantiles

# Q3, per-device row counts. Program encounters are the case a fitted lognormal gets wrong.
Q3 = {
    "subjects": dict(p50=464, p90=5685, p99=42519),
    "enrolments": dict(p50=100, p90=1653, p99=15254),
    "program_encounters": dict(p50=89, p90=11762, p99=153126),
    "encounters": dict(p50=62, p90=3167, p99=53670),
}


@pytest.mark.parametrize("entity", sorted(Q3))
def test_every_measured_percentile_is_reproduced(entity):
    pct = Q3[entity]
    d = Quantiles.of(**pct)
    rng = random.Random(7)
    n = sorted(d.sample_int(rng) for _ in range(100_000))
    for name, expected in pct.items():
        got = n[int(float(name[1:]) / 100 * len(n))] if name != "p50" else statistics.median(n)
        assert abs(got - expected) <= expected * 0.05, f"{entity} {name}: {got} vs {expected}"


def test_the_quantile_function_is_exact_at_the_measured_points():
    d = Quantiles.of(p50=89, p90=11762, p99=153126)
    assert d.quantile(0.50) == pytest.approx(89)
    assert d.quantile(0.90) == pytest.approx(11762)
    assert d.quantile(0.99) == pytest.approx(153126)


def test_the_tail_keeps_growing_past_the_last_measured_point():
    """Clamping at p99 would cap the heaviest devices and remove the load the tail exists to make."""
    d = Quantiles.of(p50=89, p90=11762, p99=153126)
    assert d.quantile(0.999) > d.quantile(0.99)


def test_program_encounters_are_not_lognormal():
    """Recorded so the fitted-lognormal approach is not reinstated: it is 54% low at p90."""
    import math
    z99, z90 = 2.3263478740408408, 1.2815515655446004
    mu, sigma = math.log(89), (math.log(153126) - math.log(89)) / z99
    assert math.exp(mu + z90 * sigma) < 11762 * 0.6


def test_values_must_increase_with_quantile():
    with pytest.raises(ValueError, match="increase"):
        Quantiles.of(p50=100, p90=10)


def test_percentiles_must_be_distinct():
    with pytest.raises(ValueError):
        Quantiles(points=((0.5, 10.0), (0.5, 20.0)))


def test_a_single_percentile_is_not_enough():
    with pytest.raises(ValueError, match="two"):
        Quantiles.of(p50=10)


def test_non_positive_values_are_rejected():
    with pytest.raises(ValueError, match="positive"):
        Quantiles.of(p50=0, p90=10)


def test_sampling_is_reproducible_for_a_seed():
    d = Quantiles.of(**Q3["subjects"])
    assert [d.sample_int(random.Random(3)) for _ in range(5)] == \
           [d.sample_int(random.Random(3)) for _ in range(5)]
