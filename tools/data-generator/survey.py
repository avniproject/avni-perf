#!/usr/bin/env python3
"""Report what a bundle can generate, and how close that lands to production.

Run this before choosing a configuration for a load test. Section H1 makes the config source a
parameter of the run, and org shape changes what is being measured -- a small implementation will
not exercise the syncDetails row count that D1.1 identifies as a cost.

    python3 survey.py /path/to/bundle
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import statistics
import sys
from datetime import date

import bundle as bundle_mod
import observations as obs
import profile as profile_mod

SAMPLE_ROWS = 5000


def describe(path: str, seed: int, profile_path: str | None) -> int:
    prof = profile_mod.load(profile_path)
    b = bundle_mod.load(path)
    elements = sum(len(v) for v in b.forms.values())
    print(f"bundle:  {b.path}")
    print(f"profile: {prof.name}" + (f"  (measured {prof.measured_on})" if prof.measured_on else ""))
    print(f"  live concepts        {len(b.concepts)}")
    print(f"  forms                {len(b.forms)}")
    print(f"  live form mappings   {len(b.mappings)}")
    print(f"  generatable elements {elements}")
    print(f"  distinct concepts reachable through a live mapping  {len(b.concept_uuids())}")

    if not b.mappings:
        print("\nNo live form mappings. Nothing can be generated from this bundle.")
        return 1

    by_type = collections.Counter(m.form_type for m in b.mappings)
    print("\nmappings by form type:")
    for t, n in sorted(by_type.items()):
        covered = sum(len(b.elements_for(m)) for m in b.mappings if m.form_type == t)
        print(f"  {t:34s} {n:3d} mapping(s), {covered:4d} generatable element(s)")

    missing = sorted(set(prof.targets) - set(by_type))
    if missing:
        print(f"\n  not present: {', '.join(missing)}")
        print("  rows of those kinds cannot be generated from this bundle.")

    print(f"\nprojected observations, {SAMPLE_ROWS} sampled rows per form type:")
    print(f"  {'form type':<26} {'keys p50':>9} {'p95':>5} {'bytes':>7}   target")
    anchor = date.today()
    for form_type, target in prof.targets.items():
        p50, p95 = target.key_count.p50, target.key_count.p95
        mappings = [m for m in b.mappings if m.form_type == form_type]
        if not mappings:
            continue
        els = max((b.elements_for(m) for m in mappings), key=len)
        if not els:
            continue
        rng = random.Random(seed)
        kc = target.key_count
        rows = [obs.generate(els, kc, rng, anchor) for _ in range(SAMPLE_ROWS)]
        n = sorted(len(r) for r in rows)
        size = statistics.mean(len(json.dumps(r).encode()) for r in rows)
        note = ""
        if len(els) < p95:
            note = f"  <- only {len(els)} elements, cannot reach p95 {p95}"
        print(f"  {form_type:<26} {statistics.median(n):>9.0f} {n[int(0.95*len(n))]:>5d} "
              f"{size:>7.0f}   {target.table} {p50:g}/{p95:g}"
              f"{'/' + str(target.mean_bytes) if target.mean_bytes else ''}{note}")

    print("\nConcept cardinality is a whole-platform property, not a per-org one. Production's "
          "5,623\ndistinct observation keys span every organisation, so total cardinality comes "
          "from tenant\ncount rather than from any single bundle. See H3.")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("bundle", help="path to an exported Avni implementation bundle")
    ap.add_argument("--seed", type=int, default=42, help="seed, for a reproducible sample")
    ap.add_argument("--profile", default=None,
                    help=f"distribution targets (default: {profile_mod.DEFAULT.name})")
    args = ap.parse_args(argv)
    try:
        return describe(args.bundle, args.seed, args.profile)
    except (NotADirectoryError, FileNotFoundError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
