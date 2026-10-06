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
from dataclasses import replace
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
        alts = [a for a in raw.get("address_level_types", [])
                if a.get("organisation_id") == org]
        if not sts:
            missing.append(("subject type", org))
        # Encounter types were not checked, and nothing downstream guards them: `rows.py` indexes
        # `ctx.encounter_types` directly, so an empty list fails with an IndexError deep inside
        # generation rather than here. Programmes are guarded (`if ctx.programs`), which is why
        # they are absent from this check -- a deployment with no programmes simply generates no
        # enrolments, and with the programme design out of scope that is the expected shape.
        if not ets:
            missing.append(("encounter type", org))
        # Where this tenant's subjects may be registered. The generator uses one subject type
        # per tenant (`ctx.subject_types[0]`), so only that one's entry matters.
        #
        # **An empty list here is not the same as no restriction.** No entry for the subject type
        # means registration is unrestricted and the whole catchment counts; an entry naming types
        # means the sync scope query intersects the catchment with exactly those, and an empty
        # intersection matches nothing. Placing subjects below the permitted level is what made
        # org 3's 900 individuals invisible while every privilege resolved correctly.
        by_uuid = {a["uuid"]: a["id"] for a in alts}
        reg = []
        if sts:
            for entry in raw.get("registration_locations", []):
                # Both filters are needed. The uuid alone does not identify an organisation --
                # every organisation importing this bundle gets the same subject type uuid -- so
                # matching on it alone hands each tenant the union of every tenant's rules.
                if entry.get("organisation_id") != org:
                    continue
                if entry.get("subject_type_uuid") != sts[0].uuid:
                    continue
                for u in entry.get("location_type_uuids") or []:
                    if u in by_uuid:
                        reg.append(by_uuid[u])
                    else:
                        missing.append((f"registration location type {u}", org))
        out[org] = (sts, prs, ets, alts, sorted(set(reg)))
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
    ap.add_argument("--bundle-root", default=None,
                    help="directory holding one extracted bundle per archetype, for a recipe "
                         "whose tenants name a bundle_archetype")
    ap.add_argument("--profile", default=None, help="override the recipe's profile")
    ap.add_argument("--allow-bundle-mismatch", action="store_true",
                    help="generate even though the bundle is not the one the recipe names")
    ap.add_argument("--no-hash", action="store_true",
                    help="skip content hashing in the manifest, for a quick throwaway build")
    ap.add_argument("--feeder-only", action="store_true",
                    help="write only sync-users.csv, for a dataset that is already loaded")
    ap.add_argument("--supervisor-push-scale", type=float, default=1.0,
                    help="pushScale for supervisors in the feeder (default 1.0)")
    args = ap.parse_args(argv)

    recipe = recipe_mod.Recipe.load(args.recipe)
    deployment = recipe.to_deployment()

    # A tenant may carry its own bundle. H1 makes organisation complexity a load variable: the
    # number of entities a config defines is the number of rows posted to syncDetails, and
    # therefore the per-row queries filterChangedEntities runs. --bundle overrides the
    # deployment-wide fallback, not a tenant's own choice.
    # **An archetype that does not resolve must stop the run, not fall back.** Unresolved, a
    # tenant drops through to the deployment-wide bundle and generates at the wrong configuration
    # -- which loads cleanly, and config size is precisely the variable these archetypes exist to
    # vary. 513 co-tenants would be built from one config and nothing would say so.
    unresolved = recipe.unresolved_archetypes(args.bundle_root)
    if unresolved:
        counts = recipe.archetypes()
        print(f"error: this recipe assigns tenants to bundle archetypes and "
              + ("--bundle-root was not given" if args.bundle_root is None
                 else f"{args.bundle_root} has no directory for: {', '.join(unresolved)}"),
              file=sys.stderr)
        for a in sorted(counts):
            print(f"       {a:<24} {counts[a]:>4} tenants", file=sys.stderr)
        print(f"       Extract one bundle per archetype into a directory of that name and pass "
              f"--bundle-root. Without it every tenant would be built from the same config.",
              file=sys.stderr)
        return 2

    paths = recipe.bundle_paths(args.bundle_root)
    if args.bundle:
        # --bundle is the deployment-wide fallback, so a tenant's own choice outranks it --
        # whether that choice is an explicit path or an archetype already resolved above.
        # Overwriting a resolved archetype here would undo the refusal a few lines up.
        paths = {org: (paths[org] if (recipe.tenants[i].get("bundle_path")
                                      or recipe.tenants[i].get("bundle_archetype"))
                       else args.bundle)
                 for i, org in enumerate(paths)}
    for org, path in sorted(paths.items()):
        if not path or not Path(path).is_dir():
            print(f"error: organisation {org} has no bundle directory: {path}\n"
                  f"       the committed recipes leave it unset on purpose -- pass --bundle, or "
                  f"set bundle_path or bundle_archetype per tenant", file=sys.stderr)
            return 2
    if recipe.archetypes():
        for a, n in sorted(recipe.archetypes().items()):
            print(f"  archetype {a:<24} {n:>4} tenants")

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
        for kind, org in missing:
            print(f"error: no {kind} for organisation {org}", file=sys.stderr)
        print("\nThese come from the implementation bundle, and refs.json is dumped from the "
              "database after it is loaded.\nLoad the bundle into each tenant, re-run refs.sql, "
              "and try again.", file=sys.stderr)
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

    # **--feeder-only still runs every check above.** The bundle has to be present and match the
    # recipe, because the point of the feeder is that it names the users the load actually created
    # -- and that guarantee comes from building it from the same inputs, not from skipping to it.
    if args.feeder_only:
        _write_feeder(deployment, refs, args)
        return 0

    # One tenant at a time, because each has its own metadata ids.
    #
    # **The bases come from the whole deployment, not from each slice of it.** `plan_ids` hands
    # out a disjoint range per tenant precisely so rows from different tenants cannot collide —
    # but computing it on a one-tenant deployment returns the base for tenant *zero* every time,
    # so all ten pilot tenants were being allocated the same range. Nothing had caught it because
    # no multi-tenant dataset has ever been loaded; it would have surfaced as primary key
    # violations partway through Day 7.
    bases = dep.plan_ids(deployment)

    counts: dict[str, int] = {}
    for spec in deployment.tenants:
        sts, prs, ets, alts, reg = refs[spec.organisation_id]
        # `replace` rather than a fresh DeploymentSpec: the hand-written version dropped
        # `id_base` when it was added, which is the third time a field has gone missing from a
        # list like that. This one cannot.
        one = replace(deployment, tenants=(spec,), id_base=bases[spec.organisation_id])
        part = dep.write_dataset(one, bundles[spec.organisation_id], profile, columns,
                                 Path(args.out) / spec.name,
                                 subject_types=sts, programs=prs, encounter_types=ets,
                                 address_level_types=alts, registration_type_ids=reg,
                                 recipe_name=recipe.name, hash_files=not args.no_hash)
        for t, n in part.items():
            counts[t] = counts.get(t, 0) + n
        print(f"  {spec.name:<10} {sum(part.values()):>12,} rows")

    total = sum(counts.values())
    print(f"\n  {total:,} rows written under {args.out}")
    print(f"  load each tenant's directory in turn, then run validate.py -- H5 is the gate, "
          f"not this script")
    _write_feeder(deployment, refs, args)
    return 0


def _write_feeder(deployment, refs, args) -> None:
    """The simulation's user file, spanning every tenant.

    **This was documented as happening and did not happen.** The README said generate.py writes
    `sync-users.csv` via `feeder_csv`; nothing called it, and the file in the repository was a
    ten-row hand-made one naming a single organisation while the cases need 500 to 1,692 users.
    The function existed and was tested, so it read as wired up.

    **Built from the same refs the dataset was**, which is the whole reason it belongs here rather
    than in a script of its own: `build_tenant` derives the hierarchy from the target's address
    level types, so a feeder built from anything else names users the server has never heard of,
    in a file that is perfectly well-formed.
    """
    feeder = Path(args.out) / "sync-users.csv"
    n = dep.feeder_csv(
        deployment, feeder,
        supervisor_push_scale=args.supervisor_push_scale,
        refs_by_organisation={org: (r[3], r[4]) for org, r in refs.items()})
    print(f"\n  {n:,} users written to {feeder}")
    print(f"  copy it to src/gatling/resources/sync-users.csv to run against this dataset")
    if args.supervisor_push_scale == 1.0:
        print("  SUPERVISOR_PUSH_SCALE is 1.0, so every supervisor pushes as much as a field "
              "worker.\n  The deployment says that is wrong in a known direction -- a supervisor "
              "pulls a wide\n  catchment and creates almost nothing. Pass --supervisor-push-scale "
              "if a better figure exists.")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
