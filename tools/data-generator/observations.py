"""Generate observation values that are valid for the concepts a form actually carries.

An observation is a JSONB map keyed by concept UUID. What makes a value valid depends on the
concept's datatype and, for Coded concepts, on that concept's own answer set -- which is why this
cannot be done without reading the bundle first.

Two properties matter more than the values themselves, both from section H3:

  * The number of keys per row has to reproduce a distribution, not a constant. A generator
    emitting a fixed key count builds a GIN index of the wrong shape even when the mean matches.
  * Values have to spread across each concept's answer set, because coded-value cardinality drives
    the same index.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from bundle import Element

# 95th percentile of the standard normal, for fitting a lognormal to two percentiles.
_Z95 = 1.6448536269514722


@dataclass(frozen=True)
class KeyCount:
    """Samples a per-row key count reproducing an observed median and 95th percentile.

    Fitted as a lognormal, which is the shape a fill-rate distribution takes: a floor of zero, a
    dense body, and a long right tail. Both percentiles are matched by construction --
    exp(mu) is the median, and exp(mu + 1.645*sigma) the 95th.

    Production, measured by Q6:

        program_encounter  p50 12  p95 34
        individual         p50  7  p95 29
        encounter          p50  4  p95 22
        program_enrolment  p50  2  p95 20
    """
    p50: float
    p95: float

    def __post_init__(self) -> None:
        if self.p50 <= 0:
            raise ValueError("p50 must be positive")
        if self.p95 < self.p50:
            raise ValueError("p95 must be at least p50")

    @property
    def _mu(self) -> float:
        return math.log(self.p50)

    @property
    def _sigma(self) -> float:
        return (math.log(self.p95) - math.log(self.p50)) / _Z95

    def sample(self, rng: random.Random, cap: int) -> int:
        """A key count in [0, cap]. `cap` is how many elements the form actually has."""
        if cap <= 0:
            return 0
        if self._sigma == 0:
            return min(int(round(self.p50)), cap)
        n = int(round(math.exp(rng.normalvariate(self._mu, self._sigma))))
        return max(0, min(n, cap))


def _numeric(concept, rng: random.Random) -> float:
    lo = concept.low_absolute if concept.low_absolute is not None else 0.0
    hi = concept.high_absolute if concept.high_absolute is not None else lo + 100.0
    if hi < lo:
        lo, hi = hi, lo
    v = rng.uniform(lo, hi)
    # Real numeric answers are typed by a person, so they are not dense reals.
    return round(v, 1) if hi - lo < 100 else float(round(v))


def _text(concept, rng: random.Random) -> str:
    return f"{concept.name[:24].strip() or 'text'} {rng.randrange(1000, 9999)}"


def _date(rng: random.Random, anchor: date, window_days: int) -> str:
    return (anchor - timedelta(days=rng.randrange(0, max(window_days, 1)))).isoformat()


def _date_time(rng: random.Random, anchor: date, window_days: int) -> str:
    d = anchor - timedelta(days=rng.randrange(0, max(window_days, 1)))
    stamp = datetime(d.year, d.month, d.day, rng.randrange(24), rng.randrange(60), rng.randrange(60))
    return stamp.isoformat() + ".000Z"


def value_for(
    element: Element,
    rng: random.Random,
    anchor: date,
    window_days: int = 365,
    reference_uuids: dict[str, list[str]] | None = None,
):
    """A valid value for one element, or None when nothing valid can be produced."""
    concept = element.concept
    dt = concept.data_type

    if dt == "Coded":
        if not concept.answer_uuids:
            return None
        if element.multi_select:
            # Multi-select answers cluster low: most rows pick one, a few pick several.
            k = min(1 + int(rng.expovariate(1.2)), len(concept.answer_uuids))
            return list(rng.sample(concept.answer_uuids, k))
        return rng.choice(concept.answer_uuids)

    if dt == "Numeric":
        return _numeric(concept, rng)
    if dt == "Text" or dt == "Notes":
        return _text(concept, rng)
    if dt == "Id":
        return f"ID-{rng.randrange(10**6, 10**7)}"
    if dt == "Date":
        return _date(rng, anchor, window_days)
    if dt == "DateTime":
        return _date_time(rng, anchor, window_days)
    if dt == "Time":
        return f"{rng.randrange(24):02d}:{rng.randrange(60):02d}"
    if dt == "Duration":
        return {"durationValue": rng.randrange(1, 60), "durationUnit": "days"}
    if dt in ("Subject", "Location", "Encounter", "PhoneNumber"):
        pool = (reference_uuids or {}).get(dt) or []
        if not pool:
            return None
        return rng.choice(pool)

    return None


def generate(
    elements: list[Element],
    key_count: KeyCount,
    rng: random.Random,
    anchor: date,
    window_days: int = 365,
    reference_uuids: dict[str, list[str]] | None = None,
) -> dict:
    """One observation map for a row on this form.

    Mandatory elements are filled first, because the application treats them as required. The
    remainder are drawn at random up to the sampled key count, so which concepts appear varies
    row to row -- a generator that always fills the same elements produces a narrower index than
    production's regardless of how many keys each row carries.
    """
    if not elements:
        return {}

    target = key_count.sample(rng, len(elements))
    mandatory = [e for e in elements if e.mandatory]
    optional = [e for e in elements if not e.mandatory]
    rng.shuffle(optional)

    chosen = mandatory[:target] if len(mandatory) >= target else mandatory + optional[:target - len(mandatory)]

    out: dict = {}
    for element in chosen:
        v = value_for(element, rng, anchor, window_days, reference_uuids)
        if v is not None:
            out[element.concept.uuid] = v
    return out
