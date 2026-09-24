"""Make a dataset auditable without storing it.

A generated dataset runs to gigabytes and is a pure function of its inputs, so the repository holds
the recipe rather than the output. Three small files per named dataset:

  * **the recipe** -- every input, so the dataset can be rebuilt exactly. Written by hand, read by
    the generator.
  * **the manifest** -- row counts and a content hash per table. The fingerprint: a rebuild that
    produces different numbers means something changed, and you find out before a run rather than
    during one.
  * **the verdict** -- H5's statistical gate output, recording that this dataset was blessed and
    against which profile.

**Storing the output instead would discard the one safety property the generator has.** `schema.py`
refuses to generate against a schema it does not recognise; a committed `.tsv` carries no such guard,
so a dataset built against an older migration loads into a newer database either confusingly or with
a column silently empty.

**Reproducibility depends on the bundle, which is deliberately not in this repository.** So the
recipe records which bundle, its revision, and a hash of the files that decide what can be generated.
Without that a recipe is a promise the repository cannot keep.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

SCHEMA_VERSION = 1


def _git(*args: str) -> str | None:
    try:
        out = subprocess.run(("git", *args), capture_output=True, text=True,
                             cwd=Path(__file__).parent, timeout=10)
        return out.stdout.strip() or None
    except Exception:
        return None


def _sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(chunk):
            h.update(block)
    return h.hexdigest()


def bundle_fingerprint(bundle_path: str | Path) -> dict:
    """Hash the bundle files that decide what can be generated.

    Only those three. Hashing the whole directory would make an unrelated change to a dashboard or
    a translation look like a change to the dataset.
    """
    p = Path(bundle_path)
    parts: dict[str, str] = {}
    for name in ("concepts.json", "formMappings.json"):
        f = p / name
        if f.exists():
            parts[name] = _sha256_file(f)
    forms = p / "forms"
    if forms.is_dir():
        h = hashlib.sha256()
        for f in sorted(forms.glob("*.json")):
            h.update(f.name.encode())
            h.update(_sha256_file(f).encode())
        parts["forms/"] = h.hexdigest()
    combined = hashlib.sha256(
        json.dumps(parts, sort_keys=True).encode()).hexdigest() if parts else None
    return {"files": parts, "combined": combined}


@dataclass
class Recipe:
    """Every input needed to rebuild a dataset exactly."""
    name: str
    days: int
    reference_date: str
    seed: int
    profile: str
    bundle_path: str
    bundle_revision: str | None = None
    bundle_fingerprint: dict = field(default_factory=dict)
    # Fingerprint per tenant, for tenants carrying their own bundle. H1 makes organisation
    # complexity a load variable, so a deployment covering a range of config sizes has several.
    tenant_bundle_fingerprints: dict = field(default_factory=dict)
    tenants: list[dict] = field(default_factory=list)
    enrolment_rate: float = 0.22
    program_encounter_share: float = 0.59
    notes: str | None = None
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def from_deployment(cls, name: str, deployment, *, profile: str, bundle_path: str,
                        bundle_revision: str | None = None, notes: str | None = None) -> "Recipe":
        return cls(
            name=name,
            days=deployment.days,
            reference_date=deployment.reference.isoformat(),
            seed=deployment.seed,
            profile=profile,
            bundle_path=str(bundle_path),
            bundle_revision=bundle_revision,
            bundle_fingerprint=bundle_fingerprint(bundle_path),
            # Every field, taken from the dataclass rather than listed here.
            #
            # This used to be a hand-written list and it had silently fallen two fields behind:
            # `workers_per_supervisor`, which sets how many supervisors a tenant has and how wide
            # each catchment is, and `total_encounters`, which is how every co-tenant is sized.
            # A recipe missing either rebuilds a different dataset while claiming to be the same
            # one -- and `TenantSpec` gives absent fields their defaults, so nothing raises.
            #
            # `asdict` closes it by construction: a field added to TenantSpec is captured without
            # anyone remembering to come here. The round-trip test is what keeps that true.
            tenants=[asdict(t) for t in deployment.tenants],
            enrolment_rate=deployment.enrolment_rate,
            program_encounter_share=deployment.program_encounter_share,
            notes=notes,
        )

    def to_deployment(self):
        """Rebuild the deployment this recipe describes."""
        from datetime import date

        import deployment as dep
        return dep.DeploymentSpec(
            tenants=tuple(dep.TenantSpec(**t) for t in self.tenants),
            days=self.days,
            reference=date.fromisoformat(self.reference_date),
            seed=self.seed,
            enrolment_rate=self.enrolment_rate,
            program_encounter_share=self.program_encounter_share,
        )

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Recipe":
        raw = json.loads(Path(path).read_text())
        version = raw.pop("schema_version", 0)
        if version != SCHEMA_VERSION:
            raise ValueError(
                f"recipe {path} is schema version {version}, this code reads {SCHEMA_VERSION}. "
                f"An old recipe may not describe the same dataset it once did.")
        return cls(schema_version=version, **raw)

    def bundle_paths(self) -> dict[int, str]:
        """The bundle each tenant is built from, falling back to the deployment's."""
        return {t["organisation_id"]: (t.get("bundle_path") or self.bundle_path)
                for t in self.tenants}

    def fingerprint_tenants(self) -> None:
        """Record a fingerprint for every distinct bundle this recipe references."""
        for org, path in self.bundle_paths().items():
            if path and Path(path).is_dir():
                self.tenant_bundle_fingerprints[str(org)] = bundle_fingerprint(path)

    def check_tenant_bundles(self) -> list[str]:
        """Whether each tenant's bundle is the one it was built from."""
        problems = []
        for org, path in sorted(self.bundle_paths().items()):
            recorded = self.tenant_bundle_fingerprints.get(str(org))
            if not recorded or not recorded.get("combined"):
                continue
            if not path or not Path(path).is_dir():
                problems.append(f"organisation {org}: bundle path is missing: {path}")
                continue
            if bundle_fingerprint(path)["combined"] != recorded["combined"]:
                problems.append(f"organisation {org}: bundle differs from the one recorded. "
                                f"Its data will not be the same.")
        return problems

    def check_bundle(self, bundle_path: str | Path) -> list[str]:
        """Whether the bundle on disk is the one this recipe was built from."""
        if not self.bundle_fingerprint.get("combined"):
            return ["the recipe carries no bundle fingerprint, so this cannot be checked"]
        now = bundle_fingerprint(bundle_path)
        if now["combined"] == self.bundle_fingerprint["combined"]:
            return []
        changed = [k for k, v in now["files"].items()
                   if self.bundle_fingerprint["files"].get(k) != v]
        missing = [k for k in self.bundle_fingerprint["files"] if k not in now["files"]]
        return [f"bundle differs from the one this recipe was built from"
                f"{': ' + ', '.join(sorted(changed + missing)) if changed or missing else ''}. "
                f"The dataset will not be the same."]


@dataclass
class Manifest:
    """What a build actually produced. The fingerprint a rebuild is checked against."""
    recipe: str
    generated_at: str
    tables: dict[str, dict] = field(default_factory=dict)
    provenance: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def of(cls, recipe_name: str, directory: str | Path, counts: dict[str, int],
           *, hash_files: bool = True) -> "Manifest":
        d = Path(directory)
        tables = {}
        for table, n in sorted(counts.items()):
            f = d / f"{table}.tsv"
            entry: dict = {"rows": n}
            if f.exists():
                entry["bytes"] = f.stat().st_size
                if hash_files:
                    entry["sha256"] = _sha256_file(f)
            tables[table] = entry
        return cls(
            recipe=recipe_name,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            tables=tables,
            provenance={
                "generator_commit": _git("rev-parse", "HEAD"),
                "generator_dirty": bool(_git("status", "--porcelain")),
                "python": platform.python_version(),
            },
        )

    @property
    def total_rows(self) -> int:
        return sum(t.get("rows", 0) for t in self.tables.values())

    def differences(self, other: "Manifest") -> list[str]:
        """What changed between two builds. Empty means the rebuild is identical."""
        out = []
        for table in sorted(set(self.tables) | set(other.tables)):
            a, b = self.tables.get(table), other.tables.get(table)
            if a is None or b is None:
                out.append(f"{table}: present in only one build")
                continue
            if a.get("rows") != b.get("rows"):
                out.append(f"{table}: {a['rows']:,} rows against {b['rows']:,}")
            elif a.get("sha256") and b.get("sha256") and a["sha256"] != b["sha256"]:
                out.append(f"{table}: same row count, different content")
        return out

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(asdict(self), indent=2) + "\n")
        return p

    @classmethod
    def load(cls, path: str | Path) -> "Manifest":
        raw = json.loads(Path(path).read_text())
        raw.pop("schema_version", None)
        return cls(schema_version=SCHEMA_VERSION, **raw)


def verdict_document(recipe_name: str, report) -> dict:
    """H5's gate output, as the record that a dataset was blessed and against what."""
    return {
        "schema_version": SCHEMA_VERSION,
        "recipe": recipe_name,
        "profile": report.profile_name,
        "checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "verdict": "pass" if report.ok else "fail",
        "counts": {"checks": len(report.checks),
                   "failed": len(report.failed),
                   "warned": len(report.warned)},
        "checks": [{"name": c.name, "table": c.table, "verdict": c.verdict.value,
                    "observed": c.observed, "expected": c.expected,
                    "ratio": round(c.ratio, 4) if c.ratio is not None else None,
                    "detail": c.detail}
                   for c in report.checks],
        "generator_commit": _git("rev-parse", "HEAD"),
    }
