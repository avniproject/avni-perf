"""The distribution targets a generated dataset aims at.

Kept as data rather than code for three reasons. The numbers are measurements and will move when
production is measured again. A run has to be able to say which shape it targeted (A11 records run
metadata). And a run that deliberately targets something other than today's production -- a larger
organisation, a heavier fill rate -- should say so in a file rather than a patch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from distribution import Quantiles
from observations import KeyCount

DEFAULT = Path(__file__).parent / "profiles" / "production-2026-09.json"


@dataclass(frozen=True)
class FormTypeTarget:
    form_type: str
    table: str
    key_count: KeyCount
    mean_bytes: int | None = None


@dataclass(frozen=True)
class TemporalSpread:
    """How old a table's rows are, and how often one is edited after it was created.

    Per table, because Q14 found them sharply different. Three quarters of program encounters are
    edited and the median edit lands 32 days after creation, against 383 to 595 days for encounters
    and subjects -- the scheduled-visit pattern, where a row is created when a visit is booked and
    filled in when it happens.
    """
    table: str
    age_days: Quantiles
    edited_after_creation_fraction: float
    median_days_to_first_edit: float | None = None


@dataclass(frozen=True)
class Profile:
    name: str
    measured_on: str | None
    source: str | None
    targets: dict[str, FormTypeTarget]
    catchment: dict[str, Quantiles]
    temporal: dict[str, TemporalSpread] = field(default_factory=dict)

    def for_form_type(self, form_type: str) -> FormTypeTarget | None:
        return self.targets.get(form_type)

    def rows_per_user(self, entity: str) -> Quantiles | None:
        return self.catchment.get(entity)

    def temporal_for(self, table: str) -> TemporalSpread | None:
        return self.temporal.get(table)

    @property
    def unmeasured_inputs(self) -> list[str]:
        """Inputs carrying a guess rather than a measurement. A run should report these."""
        return []


def load(path: str | Path | None = None) -> Profile:
    p = Path(path) if path else DEFAULT
    if not p.exists():
        raise FileNotFoundError(f"profile not found: {p}")
    raw = json.loads(p.read_text())

    form_types = raw.get("form_types")
    if not form_types:
        raise ValueError(f"profile {p} declares no form_types")

    targets = {}
    for form_type, t in form_types.items():
        for required in ("p50_keys", "p95_keys"):
            if required not in t:
                raise ValueError(f"profile {p}: {form_type} is missing {required}")
        targets[form_type] = FormTypeTarget(
            form_type=form_type,
            table=t.get("table", ""),
            key_count=KeyCount(p50=t["p50_keys"], p95=t["p95_keys"]),
            mean_bytes=t.get("mean_bytes"),
        )

    catchment = {}
    for entity, qs in (raw.get("catchment_rows_per_user") or {}).items():
        if entity == "note":
            continue
        pct = {k: v for k, v in qs.items() if k.startswith("p")}
        if not pct:
            raise ValueError(f"profile {p}: {entity} declares no percentiles")
        catchment[entity] = Quantiles.of(**pct)

    temporal = {}
    for table, t in ((raw.get("temporal_spread") or {}).get("tables") or {}).items():
        ages = t.get("age_days") or {}
        if not ages:
            raise ValueError(f"profile {p}: temporal_spread.{table} declares no age_days")
        frac = float(t.get("edited_after_creation_fraction", 0.0))
        if not 0.0 <= frac <= 1.0:
            raise ValueError(f"profile {p}: {table} edited fraction must be between 0 and 1")
        temporal[table] = TemporalSpread(
            table=table,
            age_days=Quantiles.of(**ages),
            edited_after_creation_fraction=frac,
            median_days_to_first_edit=t.get("median_days_to_first_edit"),
        )

    return Profile(
        name=raw.get("name", p.stem),
        measured_on=raw.get("measured_on"),
        source=raw.get("source"),
        targets=targets,
        catchment=catchment,
        temporal=temporal,
    )
