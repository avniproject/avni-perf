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
     * Reference, and the shape the customer's profile borrows for registrations and enrolments,
     * which have no customer figure of their own. **No longer the co-tenant setting** -- see
     * {@link #coTenant()}, which measures the same thing from the other end and gets a larger
     * answer.
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
     * Production's push volumes as the **server** counts them, for the co-tenant load.
     *
     * **Q17 and this measure different things, and the co-tenant load wants this one.** Q17 reads
     * `sync_telemetry`, which is the client's own report of how many records it pushed. This counts
     * `POST` requests in `AuthenticationFilter`'s log. The simulation issues one request per record,
     * so for a load test the server-side count is the one that reproduces the work: a retried push
     * is a record the client counts once and the server handles twice, and the server's cost is
     * what cases 7 and 13 exist to impose.
     *
     * <pre>
     *   entity              Q17 prob/mean      measured prob/mean
     *   Individual          0.5964 / 3.3       0.6628 /  5.2
     *   ProgramEnrolment    0.3320 / 4.0       0.3763 /  6.1
     *   ProgramEncounter    0.2868 / 8.3       0.3451 / 11.4
     *   Encounter           0.2111 / 4.0       0.2646 /  5.8
     *   records per sync      6.5                11.2
     * </pre>
     *
     * **The aggregate it was chosen to reproduce.** Across 24,280 syncs reconstructed from the log
     * with a ten-minute session gap, production's request mix is **68.2% pull to 31.8% push**, and
     * 68.0% of syncs push something. The co-tenant load was reproducing the pull side and about
     * 6.5/11.2 of the push side, so the write pressure the customer competed against in cases 7 and
     * 13 was roughly 60% of production's at the same sync rate. Writes are 32% of sync requests but
     * 26% of sync server time, so the gap costs less than proportionally -- and it is still a gap
     * in the direction that matters, because index maintenance and lock contention are on the write
     * path and are shared across every tenant in the schema.
     *
     * Measured over 2026-09-10..19 and 09-28. `tools/push_shape.py` reproduces it.
     */
    public static Map<String, PushVolume> coTenant() {
        Map<String, PushVolume> m = new LinkedHashMap<>();
        m.put("Individual", new PushVolume("Individual", 0.6628, 1, 2, 19, 244, 5.2));
        m.put("ProgramEnrolment", new PushVolume("ProgramEnrolment", 0.3763, 1, 3, 21, 349, 6.1));
        m.put("ProgramEncounter", new PushVolume("ProgramEncounter", 0.3451, 1, 6, 40, 422, 11.4));
        m.put("Encounter", new PushVolume("Encounter", 0.2646, 1, 2, 20, 466, 5.8));
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
