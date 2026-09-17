#!/usr/bin/env node
/*
 * Emits the simulation's entity table from the Avni client's own EntityMetaData.
 *
 * The simulation used to carry a hand-maintained copy of this list. It drifted: entities the client
 * had gained were missing, entities it had dropped were still being requested, and one entry had a
 * typo that silently disabled an entity on every run. Generating removes that whole class of bug.
 *
 * URL construction mirrors ConventionalRestClient.getAllForEntity so the simulation requests exactly
 * what the client requests.
 */
const fs = require("fs");
const path = require("path");

const EntityMetaData = require("openchs-models/dist/EntityMetaData.js").default;
const {version: modelsVersion} = require("openchs-models/package.json");

const OUT = path.resolve(__dirname, "../../src/gatling/resources/avni-entities.json");

// ConventionalRestClient joins [apiVersion, resourceUrl ?? resourceName, searchFilter] on "/",
// dropping empty segments. serverURL is prepended at request time by the simulation.
function resourcePath(e) {
  const searchFilter = e.resourceSearchFilterURL ? `search/${e.resourceSearchFilterURL}` : "";
  return [e.apiVersion, e.resourceUrl || e.resourceName, searchFilter]
    .filter((p) => p !== undefined && p !== null && p !== "")
    .join("/");
}

// ConventionalRestClient sets privilegeParam AND apiQueryParamKey, each to the same entityTypeUuid -
// they are not alternatives. The five EntityApprovalStatus entities declare both, and the server's
// endpoint reads entityTypeUuid (the apiQueryParamKey), so emitting only one drops the parameter
// that decides the result. Both are emitted, in the order the client merges them.
function entityTypeUuidParams(e) {
  return [e.privilegeParam, e.apiQueryParamKey].filter(Boolean);
}

// Static query params the client always sends for this entity, e.g. {"deviceId": null}.
// deviceId is filled in per run; null here means "the simulation supplies it".
function staticParams(e) {
  return e.apiQueryParams && Object.keys(e.apiQueryParams).length ? e.apiQueryParams : null;
}

// getRefData and getTxData both reverse the model list before pulling, so the last entity declared
// is fetched first. Emitting in pull order means the simulation does not have to know that.
const entities = EntityMetaData.model()
  .slice()
  .reverse()
  .map((e) => ({
    entityName: e.entityName,
    type: e.type,
    path: resourcePath(e),
    entityTypeUuidParams: entityTypeUuidParams(e),
    staticParams: staticParams(e),
    syncWeight: e.syncWeight === undefined ? null : e.syncWeight,
    pullRequired: e.syncPullRequired !== false,
    pushRequired: e.syncPushRequired !== false,
  }));

const out = {
  _generated: "DO NOT EDIT. Run tools/entity-metadata and commit the result.",
  _source: `openchs-models@${modelsVersion}`,
  _order: "pull order - already reversed from EntityMetaData.model()",
  entities,
};

fs.writeFileSync(OUT, JSON.stringify(out, null, 2) + "\n");

const ref = entities.filter((e) => e.type === "reference").length;
const tx = entities.filter((e) => e.type === "tx").length;
const noPull = entities.filter((e) => !e.pullRequired).length;
console.log(`wrote ${entities.length} entities (${ref} reference, ${tx} tx) from openchs-models@${modelsVersion}`);
console.log(`  ${noPull} are push-only (pullRequired false)`);
console.log(`  -> ${path.relative(process.cwd(), OUT)}`);
