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

from observations import KeyCount

DEFAULT = Path(__file__).parent / "profiles" / "production-2026-09.json"


@dataclass(frozen=True)
class FormTypeTarget:
    form_type: str
    table: str
    key_count: KeyCount
    mean_bytes: int | None = None


@dataclass(frozen=True)
class Profile:
    name: str
    measured_on: str | None
    source: str | None
    targets: dict[str, FormTypeTarget]

    def for_form_type(self, form_type: str) -> FormTypeTarget | None:
        return self.targets.get(form_type)


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

    return Profile(
        name=raw.get("name", p.stem),
        measured_on=raw.get("measured_on"),
        source=raw.get("source"),
        targets=targets,
    )
