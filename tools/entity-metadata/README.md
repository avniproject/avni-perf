# Entity metadata generator

Generates `src/gatling/resources/avni-entities.json` from the Avni client's own
`EntityMetaData`, so the simulation's entity list cannot drift from the client's.

```
cd tools/entity-metadata
npm install
npm run generate
```

## Why a pinned npm version rather than the sibling checkout

`openchs-models` is pinned here to the version `avni-client` ships. Reading a local
`../../../avni-models` checkout would tie the output to whatever happens to be on the machine —
at time of writing that checkout was two patch versions behind what the client actually ships.

Pinning means the generated table corresponds to a specific client release, the repository needs
no sibling checkout, and a version bump is an explicit, reviewable change.

**To track a new client release:** bump the version here, regenerate, and commit both the
`package.json` change and the regenerated JSON in the same commit.
