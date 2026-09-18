"""Sampling from measured percentiles, without assuming a shape.

The obvious approach is to fit a lognormal to two of the measured percentiles. It works for some of
what Q3 measured and fails badly for the rest:

    subjects            p50    464  p90  5,685  p99  42,519   lognormal p90 within 2%
    enrolments          p50    100  p90  1,653  p99  15,254   within 4%
    encounters          p50     62  p90  3,167  p99  53,670   19% low
    program_encounters  p50     89  p90 11,762  p99 153,126   54% low

Program encounters rise 132x from the median to the 90th percentile and only 13x from there to the
99th. That is not one population. Programme enrolment is optional, so most devices carry almost no
programme activity and a minority carry a great deal -- and no single lognormal covers both.

So interpolate the measured quantiles instead. Piecewise log-linear through the given points
reproduces every one of them exactly, assumes nothing about the shape between them, and needs no
fitting step to go wrong.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass


@dataclass(frozen=True)
class Quantiles:
    """An inverse CDF built from measured percentiles.

    `points` are (quantile, value) pairs, quantiles strictly between 0 and 1. Values must be
    positive -- interpolation happens in log space, which is what keeps a 370x spread from
    collapsing to a straight line dominated by its tail.
    """
    points: tuple[tuple[float, float], ...]

    def __post_init__(self) -> None:
        if len(self.points) < 2:
            raise ValueError("need at least two percentiles to interpolate between")
        qs = [q for q, _ in self.points]
        if qs != sorted(qs) or len(set(qs)) != len(qs):
            raise ValueError("percentiles must be strictly increasing")
        if not all(0.0 < q < 1.0 for q in qs):
            raise ValueError("quantiles must lie strictly between 0 and 1")
        vs = [v for _, v in self.points]
        if any(v <= 0 for v in vs):
            raise ValueError("values must be positive")
        if vs != sorted(vs):
            raise ValueError("values must increase with quantile")

    @classmethod
    def of(cls, **named: float) -> "Quantiles":
        """Build from keyword percentiles, e.g. Quantiles.of(p50=89, p90=11762, p99=153126)."""
        pts = []
        for key, value in named.items():
            if not key.startswith("p"):
                raise ValueError(f"expected a percentile like p50, got {key!r}")
            pts.append((float(key[1:]) / 100.0, float(value)))
        pts.sort()
        return cls(points=tuple(pts))

    def quantile(self, q: float) -> float:
        """The value at quantile `q`, interpolated or extrapolated in log space."""
        if not 0.0 < q < 1.0:
            raise ValueError("q must lie strictly between 0 and 1")
        pts = self.points

        # Inside the measured range: interpolate between the bracketing pair.
        for (q0, v0), (q1, v1) in zip(pts, pts[1:]):
            if q0 <= q <= q1:
                if q1 == q0:
                    return v0
                f = (q - q0) / (q1 - q0)
                return math.exp(math.log(v0) + f * (math.log(v1) - math.log(v0)))

        # Outside it: continue the slope of the nearest segment rather than clamping, so the tail
        # keeps growing. Clamping would cap the heaviest devices at exactly the measured p99 and
        # remove the load the tail exists to produce.
        if q < pts[0][0]:
            (q0, v0), (q1, v1) = pts[0], pts[1]
        else:
            (q0, v0), (q1, v1) = pts[-2], pts[-1]
        slope = (math.log(v1) - math.log(v0)) / (q1 - q0)
        return math.exp(math.log(v0) + (q - q0) * slope)

    def sample(self, rng: random.Random) -> float:
        return self.quantile(rng.random())

    def sample_int(self, rng: random.Random, minimum: int = 0) -> int:
        return max(minimum, int(round(self.sample(rng))))
