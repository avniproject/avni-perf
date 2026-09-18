"""The distribution targets a generated dataset aims at.

Kept as data rather than code for three reasons. The numbers are measurements and will move when
production is measured again. A run has to be able to say which shape it targeted (A11 records run
metadata). And a run that deliberately targets something other than today's production -- a larger
organisation, a heavier fill rate -- should say so in a file rather than a patch.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
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
    """Age of `last_modified_date_time`, in days before the dataset's reference date."""
    days: Quantiles
    edited_after_creation_fraction: float
    unmeasured: bool = False
    note: str | None = None


@dataclass(frozen=True)
class Profile:
    name: str
    measured_on: str | None
    source: str | None
    targets: dict[str, FormTypeTarget]
    catchment: dict[str, Quantiles]
    temporal: TemporalSpread | None = None

    def for_form_type(self, form_type: str) -> FormTypeTarget | None:
        return self.targets.get(form_type)

    def rows_per_user(self, entity: str) -> Quantiles | None:
        return self.catchment.get(entity)

    @property
    def unmeasured_inputs(self) -> list[str]:
        """Inputs carrying a guess rather than a measurement. A run should report these."""
        out = []
        if self.temporal and self.temporal.unmeasured:
            out.append("temporal_spread")
        return out


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

    temporal = None
    t = raw.get("temporal_spread")
    if t:
        days = {k.replace("days_", ""): v for k, v in t.items() if k.startswith("days_p")}
        if not days:
            raise ValueError(f"profile {p}: temporal_spread declares no days_pNN percentiles")
        temporal = TemporalSpread(
            days=Quantiles.of(**days),
            edited_after_creation_fraction=float(t.get("edited_after_creation_fraction", 0.0)),
            unmeasured=bool(t.get("unmeasured")),
            note=t.get("note"),
        )

    return Profile(
        name=raw.get("name", p.stem),
        measured_on=raw.get("measured_on"),
        source=raw.get("source"),
        targets=targets,
        catchment=catchment,
        temporal=temporal,
    )
