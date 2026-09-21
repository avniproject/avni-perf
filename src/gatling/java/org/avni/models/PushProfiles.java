package org.avni.models;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * The two workloads the push path can model, and how an entity's volume is chosen between them.
 *
 * Kept out of the simulation class deliberately: that one cannot be loaded outside Gatling, so
 * anything living in it can only be checked by running a load test. This is the part worth
 * checking - a table of numbers and the rules that select between them.
 */
public final class PushProfiles {

    /**
     * What the platform does today, measured by Q17 over 105,718 completed syncs.
     *
     * Reference, and the right setting for the co-tenant traffic in cases 7 and 13 where
     * production's own organisations load the server alongside the customer's. Not for the
     * customer's own cases: it understates them by an order of magnitude.
     */
    public static Map<String, PushVolume> production() {
        Map<String, PushVolume> m = new LinkedHashMap<>();
        m.put("Individual", new PushVolume("Individual", 0.5964, 1, 13, 174, 3.3));
        m.put("ProgramEnrolment", new PushVolume("ProgramEnrolment", 0.3320, 1, 15, 349, 4.0));
        m.put("ProgramEncounter", new PushVolume("ProgramEncounter", 0.2868, 3, 33, 323, 8.3));
        m.put("Encounter", new PushVolume("Encounter", 0.2111, 1, 13, 479, 4.0));
        return m;
    }

    /**
     * The deployment this exercise exists to size.
     *
     * The level is the customer's: twenty encounters per field worker per day, read as the median.
     * **The spread is a modelling choice** - p95 at 45, floor at 8 - because one number is not a
     * distribution. Registrations and enrolments have no customer figure at all and borrow
     * production's shape.
     *
     * `programModel` decides which table the twenty a day land on. **Their programme design is
     * work in progress**, so the bundle exported today has no live programs while the description
     * this exercise was scoped against is an NCD programme with ten encounter types. The default
     * follows the design; `general` follows the current export. Volume is identical either way -
     * what changes is whether the write path touches `program_encounter` behind a
     * `program_enrolment` parent, or `encounter` hanging straight off the subject.
     */
    public static Map<String, PushVolume> customer(boolean programModel) {
        PushVolume theTwentyADay = new PushVolume("encounters", 1.0, 8, 20, 45, 150, 24.0);
        Map<String, PushVolume> m = new LinkedHashMap<>();
        Map<String, PushVolume> shape = production();

        m.put("Individual", shape.get("Individual"));
        m.put("ProgramEnrolment", programModel ? shape.get("ProgramEnrolment") : none("ProgramEnrolment"));
        m.put("ProgramEncounter", programModel ? as("ProgramEncounter", theTwentyADay) : none("ProgramEncounter"));
        m.put("Encounter", programModel ? none("Encounter") : as("Encounter", theTwentyADay));
        return m;
    }

    public static Map<String, PushVolume> forProfile(boolean customerProfile, boolean programModel) {
        return customerProfile ? customer(programModel) : production();
    }

    /** The same distribution under a different entity's name. */
    private static PushVolume as(String entityName, PushVolume v) {
        return new PushVolume(entityName, v.probability, v.min, v.p50, v.p95, v.max, v.mean);
    }

    /** Never pushed. A probability of zero drops the entity from the chain entirely. */
    private static PushVolume none(String entityName) {
        return new PushVolume(entityName, 0.0, 1, 1, 1, 1.0);
    }

    private PushProfiles() {
    }
}
