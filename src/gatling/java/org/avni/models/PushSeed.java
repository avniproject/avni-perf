package org.avni.models;

import java.util.List;

/**
 * What one simulated device holds, and therefore what it can create records against.
 *
 * A real client pushes records it built on top of data it already has: an encounter references an
 * enrolment it downloaded, an enrolment references a subject, and every observation is keyed by a
 * concept from the org's own forms. The simulation cannot invent any of that - a pushed record with
 * a made-up subjectTypeUUID is rejected before it reaches a table, and would measure the validation
 * path rather than the write path.
 *
 * So the values are harvested from the deployment itself, once per user (see seedChain). That keeps
 * the push path independent of how the data was created: it works against a generated dataset, a
 * restored dump, or a hand-built org, with no shared list of UUIDs to keep in step.
 *
 * Observations are carried verbatim rather than synthesised, which matters more than it looks.
 * Insert cost on this path is dominated by GIN maintenance over the observations jsonb, so the
 * number of keys and the shape of the values are the load. Real rows are the only honest source.
 */
public class PushSeed {
    /** Subjects this device can hang general encounters off. Empty disables Encounter pushes. */
    public final List<String> individualUuids;
    /** Enrolments this device can hang program encounters off. Empty disables ProgramEncounter pushes. */
    public final List<String> enrolmentUuids;

    public final String subjectTypeUuid;
    public final String genderUuid;
    public final String addressLevelUuid;
    public final String programUuid;
    public final String programEncounterTypeUuid;
    public final String encounterTypeUuid;

    /**
     * Observation arrays in push form - a JSON array of {conceptUUID, value}, ready to embed.
     * Pulled rows carry observations as a {conceptUuid: value} map, so these are converted once at
     * harvest rather than per request.
     */
    public final List<String> individualObservations;
    public final List<String> programEncounterObservations;
    public final List<String> encounterObservations;

    public PushSeed(List<String> individualUuids, List<String> enrolmentUuids,
                    String subjectTypeUuid, String genderUuid, String addressLevelUuid,
                    String programUuid, String programEncounterTypeUuid, String encounterTypeUuid,
                    List<String> individualObservations,
                    List<String> programEncounterObservations,
                    List<String> encounterObservations) {
        this.individualUuids = individualUuids;
        this.enrolmentUuids = enrolmentUuids;
        this.subjectTypeUuid = subjectTypeUuid;
        this.genderUuid = genderUuid;
        this.addressLevelUuid = addressLevelUuid;
        this.programUuid = programUuid;
        this.programEncounterTypeUuid = programEncounterTypeUuid;
        this.encounterTypeUuid = encounterTypeUuid;
        this.individualObservations = individualObservations;
        this.programEncounterObservations = programEncounterObservations;
        this.encounterObservations = encounterObservations;
    }

    /** Whether this device can push a subject: the three required references are all present. */
    public boolean canPushIndividual() {
        return subjectTypeUuid != null && addressLevelUuid != null;
    }

    public boolean canPushEnrolment() {
        return programUuid != null && !individualUuids.isEmpty();
    }

    public boolean canPushProgramEncounter() {
        return programEncounterTypeUuid != null && !enrolmentUuids.isEmpty();
    }

    public boolean canPushEncounter() {
        return encounterTypeUuid != null && !individualUuids.isEmpty();
    }

    /** What is missing, for the one-line warning when a device turns out to be unable to push. */
    public String missing() {
        StringBuilder sb = new StringBuilder();
        if (subjectTypeUuid == null) sb.append("subjectType ");
        if (addressLevelUuid == null) sb.append("addressLevel ");
        if (programUuid == null) sb.append("program ");
        if (programEncounterTypeUuid == null) sb.append("programEncounterType ");
        if (encounterTypeUuid == null) sb.append("encounterType ");
        if (individualUuids.isEmpty()) sb.append("individuals ");
        if (enrolmentUuids.isEmpty()) sb.append("enrolments ");
        return sb.length() == 0 ? "nothing" : sb.toString().trim();
    }
}
