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

// Endpoints that also exist as a Spring `Slice` under the same path plus `/v2`.
//
// **Not derivable from openchs-models** - the client does not call them, so nothing in the model
// knows they exist. This list comes from the server, and the way to re-derive it is:
//
//   grep -rn "SlicedResources<" -B 8 avni-server-api/src/main/java/org/avni/server/web \
//     | grep -oE '(value = )?"/[a-zA-Z/]+v2"' | sort -u
//
// Three sliced paths the server exposes are deliberately absent here because no pull entity uses
// them: attendanceRecord, individual and session, each under `search/lastModified`.
//
// Why it matters: a `Page` has to run a `count(*)` over the whole matching set to report
// `totalPages`. A `Slice` fetches `size + 1` rows and reports `hasNext`, with no count at all. On
// `program_encounter` - 11.4 GB with GIN indexes and row-level security on every query - that
// count is a candidate choke point in its own right, which is the whole reason the simulation
// needs to be able to drive both.
const SLICED_PATHS = new Set([
  "comment",
  "commentThread",
  "encounter",
  "entityApprovalStatus",
  "groupSubject",
  "identifierAssignment",
  "individual",
  "individualRelationship",
  "news",
  "programEncounter",
  "programEnrolment",
  "subjectMigrations",
  "subjectProgramEligibility",
  "task",
  "taskUnAssignments",
  "txNewChecklistEntity",
  "txNewChecklistItemEntity",
  "userSubjectAssignment",
]);

function slicePath(resource) {
  return SLICED_PATHS.has(resource) ? `${resource}/v2` : null;
}

// ConventionalRestClient sets privilegeParam AND apiQueryParamKey, each to the same entityTypeUuid -
// they are not alternatives. The five EntityApprovalStatus entities declare both, and the server's
// endpoint reads entityTypeUuid (the apiQueryParamKey), so emitting only one drops the parameter
// that decides the result. Both are emitted, in the order the client merges them.
function entityTypeUuidParams(e) {
  return [e.privilegeParam, e.apiQueryParamKey].filter(Boolean);
}

// ConventionalRestClient.postAllEntities builds the push URL differently from the pull URL: no
// apiVersion segment, no search filter, and the resource name pluralised at the call site. The one
// irregular plural is hard-coded there, so it is hard-coded here too.
const ES_RESOURCES = new Set(["entityApprovalStatus"]);

function pushPath(e) {
  if (e.resourceUrl) return e.resourceUrl;
  return ES_RESOURCES.has(e.resourceName) ? `${e.resourceName}es` : `${e.resourceName}s`;
}

// Static query params the client always sends for this entity, e.g. {"deviceId": null}.
// deviceId is filled in per run; null here means "the simulation supplies it".
function staticParams(e) {
  return e.apiQueryParams && Object.keys(e.apiQueryParams).length ? e.apiQueryParams : null;
}

// Plan D6.2: what a page of this entity costs the client to parse and persist, as a multiple of
// baseMsPerRecord. Three tiers deliberately — a finer split would be false precision on numbers
// this soft, and D7 replaces the whole scheme with per-entity measurements.
//
// Tiering is by payload structure, because whether a row carries an observation set is the dominant
// cost driver. It is judgement, not measurement.
const LIGHT = new Set([
  "Gender", "ProgramOutcome", "TaskStatus", "TaskType", "ApprovalStatus", "StandardReportCardType",
  "LocationHierarchy", "Privilege", "Groups", "GroupPrivileges", "MyGroups", "GroupRole",
  "MenuItem", "AddressLevel", "LocationMapping",
]);
const HEAVY = new Set(["Individual", "ProgramEnrolment", "ProgramEncounter", "Encounter"]);

function storageWeight(entityName) {
  if (LIGHT.has(entityName)) return 0.2;
  if (HEAVY.has(entityName)) return 3.0;
  return 1.0;
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
    slicePath: slicePath(resourcePath(e)),
    pushPath: e.type === "tx" ? pushPath(e) : null,
    entityTypeUuidParams: entityTypeUuidParams(e),
    staticParams: staticParams(e),
    syncWeight: e.syncWeight === undefined ? null : e.syncWeight,
    storageWeight: storageWeight(e.entityName),
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
const noPush = entities.filter((e) => e.type === "tx" && !e.pushRequired).length;
const byWeight = entities.reduce((acc, e) => {
  acc[e.storageWeight] = (acc[e.storageWeight] || 0) + 1;
  return acc;
}, {});
console.log(`wrote ${entities.length} entities (${ref} reference, ${tx} tx) from openchs-models@${modelsVersion}`);
console.log(`  ${noPull} are push-only (pullRequired false), ${noPush} tx entities are pull-only (syncPushRequired false)`);
console.log(
  `  storage weights: ` +
    Object.entries(byWeight)
      .sort((a, b) => a[0] - b[0])
      .map(([w, n]) => `${n} at ${w}x`)
      .join(", ")
);
console.log(`  -> ${path.relative(process.cwd(), OUT)}`);
