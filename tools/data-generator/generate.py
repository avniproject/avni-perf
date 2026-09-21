#!/usr/bin/env python3
"""Generate a dataset from a recipe.

    psql -d <db> -At -f columns.sql > columns.json      # the target's own columns
    psql -d <db> -At -f refs.sql    > refs.json         # its metadata ids
    python3 generate.py --recipe datasets/pilot-day-180.json \\
                        --columns columns.json --refs refs.json \\
                        --bundle /path/to/bundle --out /data/pilot-day-180

Both dumps come from the target rather than from anything committed here: 484 Flyway migrations have
already moved this schema, and the ids belong to whichever bundle was loaded.

Writes the dataset, a `load.sql`, a `summary.txt` and a `manifest.json` fingerprint. Run
`validate.py` against the loaded database afterwards -- generating is not the gate, H5 is.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import bundle as bundle_mod
import deployment as dep
import profile as profile_mod
import recipe as recipe_mod
import rows as row_gen
import schema


def _refs(path: Path, organisation_ids: set[int]):
    """Turn refs.json into the reference objects the row generator takes.

    Metadata is per organisation, so a tenant can only be generated against its own rows. A tenant
    with no subject type would otherwise produce subjects of some other tenant's type, which loads
    cleanly and is wrong in a way no statistic would catch.
    """
    raw = json.loads(path.read_text())
    missing = []
    out = {}
    for org in sorted(organisation_ids):
        sts = [row_gen.SubjectTypeRef(
                   id=s["id"], uuid=s["uuid"], name=s["name"],
                   sync_concept_1=s.get("sync_concept_1"),
                   sync_concept_2=s.get("sync_concept_2"))
               for s in raw.get("subject_types", []) if s.get("organisation_id") == org]
        prs = [row_gen.ProgramRef(id=p["id"], uuid=p["uuid"], name=p["name"])
               for p in raw.get("programs", []) if p.get("organisation_id") == org]
        ets = [row_gen.EncounterTypeRef(id=e["id"], uuid=e["uuid"], name=e["name"])
               for e in raw.get("encounter_types", []) if e.get("organisation_id") == org]
        if not sts:
            missing.append(org)
        out[org] = (sts, prs, ets)
    return out, missing


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--recipe", required=True, help="dataset recipe, from datasets/")
    ap.add_argument("--columns", required=True, help="columns.json, from columns.sql")
    ap.add_argument("--refs", required=True, help="refs.json, from refs.sql")
    ap.add_argument("--out", required=True, help="directory to write the dataset into")
    ap.add_argument("--bundle", default=None,
                    help="implementation bundle; overrides the recipe's bundle_path")
    ap.add_argument("--profile", default=None, help="override the recipe's profile")
    ap.add_argument("--allow-bundle-mismatch", action="store_true",
                    help="generate even though the bundle is not the one the recipe names")
    ap.add_argument("--no-hash", action="store_true",
                    help="skip content hashing in the manifest, for a quick throwaway build")
    args = ap.parse_args(argv)

    recipe = recipe_mod.Recipe.load(args.recipe)
    deployment = recipe.to_deployment()

    # A tenant may carry its own bundle. H1 makes organisation complexity a load variable: the
    # number of entities a config defines is the number of rows posted to syncDetails, and
    # therefore the per-row queries filterChangedEntities runs. --bundle overrides the
    # deployment-wide fallback, not a tenant's own choice.
    paths = recipe.bundle_paths()
    if args.bundle:
        paths = {org: (recipe.tenants[i].get("bundle_path") or args.bundle)
                 for i, org in enumerate(paths)}
    for org, path in sorted(paths.items()):
        if not path or not Path(path).is_dir():
            print(f"error: organisation {org} has no bundle directory: {path}\n"
                  f"       the committed recipes leave it unset on purpose -- pass --bundle, or "
                  f"set bundle_path per tenant", file=sys.stderr)
            return 2

    problems = recipe.check_tenant_bundles()
    if len(set(paths.values())) == 1:
        problems += recipe.check_bundle(next(iter(paths.values())))
    problems = [p for p in problems if "carries no bundle fingerprint" not in p]
    if problems:
        for p in problems:
            print(f"{'warning' if args.allow_bundle_mismatch else 'error'}: {p}", file=sys.stderr)
        if not args.allow_bundle_mismatch:
            print("       pass --allow-bundle-mismatch to generate anyway, and expect a dataset\n"
                  "       that does not match this recipe's name", file=sys.stderr)
            return 2
    columns = {t: list(c) for t, c in json.loads(Path(args.columns).read_text()).items()}
    try:
        schema.verify_all(columns)
    except schema.SchemaDrift as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    refs, missing = _refs(Path(args.refs), {t.organisation_id for t in deployment.tenants})
    if missing:
        print(f"error: no subject type for organisation(s) {missing}. Load the implementation "
              f"bundle into each tenant before generating.", file=sys.stderr)
        return 2

    # Load each distinct bundle once, however many tenants share it.
    loaded: dict[str, object] = {}
    bundles = {}
    for org, path in paths.items():
        if path not in loaded:
            loaded[path] = bundle_mod.load(path)
        bundles[org] = loaded[path]
    profile = profile_mod.load(args.profile) if args.profile else profile_mod.load()

    print(dep.summarise(deployment))
    print(f"\n  recipe  {recipe.name}\n  profile {profile.name}\n  out     {args.out}")
    if len(loaded) == 1:
        print(f"  bundle  {next(iter(loaded))}")
    else:
        print(f"  bundles {len(loaded)} distinct across {len(paths)} tenants:")
        for path, b in loaded.items():
            orgs = sorted(o for o, p in paths.items() if p == path)
            print(f"            {len(b.concept_uuids()):>4} concepts, "
                  f"{len(b.mappings):>3} mappings  orgs {orgs}  {path}")
    print()

    # One tenant at a time, because each has its own metadata ids.
    counts: dict[str, int] = {}
    for spec in deployment.tenants:
        sts, prs, ets = refs[spec.organisation_id]
        one = dep.DeploymentSpec(tenants=(spec,), days=deployment.days,
                                 reference=deployment.reference, seed=deployment.seed,
                                 enrolment_rate=deployment.enrolment_rate,
                                 program_encounter_share=deployment.program_encounter_share)
        part = dep.write_dataset(one, bundles[spec.organisation_id], profile, columns,
                                 Path(args.out) / spec.name,
                                 subject_types=sts, programs=prs, encounter_types=ets,
                                 recipe_name=recipe.name, hash_files=not args.no_hash)
        for t, n in part.items():
            counts[t] = counts.get(t, 0) + n
        print(f"  {spec.name:<10} {sum(part.values()):>12,} rows")

    total = sum(counts.values())
    print(f"\n  {total:,} rows written under {args.out}")
    print(f"  load each tenant's directory in turn, then run validate.py -- H5 is the gate, "
          f"not this script")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
