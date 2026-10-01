package org.avni.models;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Milliseconds of client work per record, per entity, measured from production's own server logs.
 *
 * **These replace a single coefficient that was wrong in two ways.** `BASE_MS_PER_RECORD` x a
 * uniform weight of 3.0 charged every observation-bearing entity 8.34 ms/record. Measurement says
 * they differ by 2.2x between themselves, and that 8.34 happened to land on `programEncounter` --
 * production's largest table, and the one these scenarios never write because the programme design
 * is out of scope. The entities the datasets do generate are cheaper, so the instrument was
 * pausing too long and the server was seeing roughly 60% of the request rate a real fleet produces.
 *
 * **How they were measured.** `AuthenticationFilter` logs every request with its user, its page and
 * size, and the server's own time. The interval between consecutive requests from one user, less
 * that server time, is the client's parse-and-persist plus one round trip. A client only asks for
 * page N+1 if page N came back full, so where the next request is the next page of the same entity
 * at the same size, the gap before it covers exactly `size` records -- which is how the response
 * size is known when the log does not carry it. 11 days of production, 2026-09-10 to 2026-09-19 and
 * 2026-09-28: 1.88M requests, 24,667 confirmed full pages. `tools/inter_request_gap.py`.
 *
 * **Why two profiles rather than one.** The variation is between organisations, not days: three
 * organisations hold 79% of the observations and agree to within 6% of each other, while a handful
 * of smaller ones run 10-20x slower. Those three are what a working deployment looks like, and the
 * pooled figure is what the platform looks like. So the customer's own cases use the first, and the
 * cases where production's organisations load the server alongside them use the second. This
 * mirrors `PushProfiles`, which splits the same way for the same reason.
 *
 * **What these are not.** Medians. The spread they come from is large -- `encounter` runs p50 6.4,
 * p90 55, p99 168 ms/record -- and nothing here reproduces it, so every virtual user is a p50
 * device. That is recorded in F5.2's parity record, and a per-user draw is the cheap way to fix it
 * if a run shows the regularity distorting something.
 *
 * **Only the five observation-bearing entities are overridden**, and deliberately. The
 * fast-against-pooled split was derived from `encounter` performance, and it does not carry to
 * metadata: on `concept`, `conceptAnswer`, `formElement` and `groupPrivilege` the three fast
 * organisations measured 8 to 27% *slower* than the pool, so splitting those by a classification
 * about observation writes would be inventing a difference. Those fall back to
 * `storageWeight x BASE_MS_PER_RECORD`, which measurement found close enough: the 0.2 tier gives
 * 0.56 ms/record against a measured 0.46 to 0.76, and the 1.0 tier gives 2.78 against 2.27 to 3.13.
 */
public final class StorageProfiles {

    /** The three organisations that agree, at 79% of the sample. For the customer's own cases. */
    public static final Map<String, Double> CUSTOMER;

    /** Every organisation pooled. For cases 6, 7, 12 and 13, where production's tenants are present. */
    public static final Map<String, Double> PRODUCTION;

    static {
        Map<String, Double> m = new LinkedHashMap<>();
        m.put("individual", 3.61);                // fast3 n=534, pooled n=1668
        m.put("programEnrolment", 2.88);          // fast3 n=149, pooled n=589
        m.put("encounter", 5.21);                 // fast3 n=1077, pooled n=1346
        m.put("groupSubject", 5.42);              // fast3 n=160, pooled n=1344
        m.put("programEncounter", 4.53);          // fast3 n=136, pooled n=2243
        CUSTOMER = Collections.unmodifiableMap(m);

        m = new LinkedHashMap<>();
        m.put("individual", 4.08);                // fast3 n=534, pooled n=1668
        m.put("programEnrolment", 3.74);          // fast3 n=149, pooled n=589
        m.put("encounter", 6.36);                 // fast3 n=1077, pooled n=1346
        m.put("groupSubject", 7.36);              // fast3 n=160, pooled n=1344
        m.put("programEncounter", 8.29);          // fast3 n=136, pooled n=2243
        PRODUCTION = Collections.unmodifiableMap(m);
    }

    private StorageProfiles() {
    }

    /** The named profile, defaulting to the customer's as `PUSH_PROFILE` does. */
    public static Map<String, Double> byName(String name) {
        return "production".equalsIgnoreCase(name) ? PRODUCTION : CUSTOMER;
    }
}
