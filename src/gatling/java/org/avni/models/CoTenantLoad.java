package org.avni.models;

import java.util.ArrayList;
import java.util.Collections;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/**
 * How production's own organisations divide the sync load between them, measured.
 *
 * **The co-tenant load was uniform and production's is not remotely.** `CO_TENANT_SYNCS_PER_HOUR`
 * drives 792 syncs an hour through a `circular()` feeder, which spreads them evenly across every
 * row in the co-tenant user file -- so across all 513 generated tenants, in proportion to how many
 * users each has, which is to say in proportion to the subjects it holds. Production's traffic does
 * not follow the data at all:
 *
 * <pre>
 *   rank 1    16.0% of device sync requests       top 3    41.1%
 *   rank 2    13.2%                              top 8    66.3%
 *   rank 3    11.8%                              top 16   83.9%
 *   rank 16    1.2%                              top 32   94.4%
 * </pre>
 *
 * **110 organisations make a device sync request at all** in eleven days -- 11.2% of the 986 Q12
 * counted, and 21.4% of the 513 that hold data. The other four fifths hold rows and sync nothing.
 *
 * **Why this changes a result rather than just a number.** Avni is shared-schema: every tenant's
 * rows live in the same tables and the same indexes, so write contention and index maintenance
 * depend on the aggregate rate and not on who produced it. What the distribution does change is the
 * **working set**. 16 busy organisations keep their pages in `shared_buffers`; 513 lightly-busy ones
 * touch five times the pages for the same request rate and evict each other. That lands on the
 * customer's own syncs as a buffer cache hit rate, which is exactly what cases 7 and 13 are trying
 * to measure.
 *
 * Measured from `AuthenticationFilter` over 2026-09-10..19 and 09-28: 1,883,217 requests, of which
 * 1,143,308 are device sync (pull, push and syncDetails rather than `/api`, `executeQuery` or
 * media). **The classification is part of the measurement rather than an afterthought**: the
 * largest organisation by request count is 88% *not* device sync -- 58.8% of its requests are
 * media and only 12.2% are a device syncing -- and the fourth by request count is 59.9% `/api`.
 * Ranking by request count alone would have modelled two integrations as device fleets. Rank here
 * is therefore share of device sync, which is a different ordering: the largest by that measure is
 * second by request count.
 *
 * Organisations are referred to by rank and archetype rather than by name throughout this
 * repository. The mapping is kept locally and is not committed.
 *
 * **What this assumes, and it is not verified.** Rank here is traffic; the co-tenant dataset's rank
 * is subjects held. Mapping one onto the other assumes an organisation's share of traffic tracks
 * its share of data. That is plausible -- more subjects, more encounters, more syncs -- and the logs
 * cannot confirm it, because they carry no subject counts. The contrary evidence worth knowing:
 * the busiest organisation in eleven days has 319 distinct users, while the co-tenant model gives
 * its rank-1 tenant 570 field workers.
 */
public final class CoTenantLoad {

    /** Share of all device sync requests held by the organisation at this rank. */
    private static final double[][] MEASURED_SHARE = {
        {1, 0.16038}, {2, 0.13244}, {3, 0.11817}, {5, 0.05338}, {8, 0.03997},
        {16, 0.01174}, {32, 0.00384}, {64, 0.00037}, {100, 0.00004},
    };

    /** Organisations that make any device sync request in an eleven-day window. */
    public static final int ACTIVE_ORGANISATIONS = 110;

    /** Of the organisations that hold data, the share of them that sync at all. */
    public static final double ACTIVE_FRACTION_OF_ORGANISATIONS_WITH_DATA = 110.0 / 513.0;

    private CoTenantLoad() {
    }

    /**
     * The measured share at a rank, interpolated in log-log space between the ranks measured.
     *
     * Interpolated rather than fitted, for the reason `co_tenants.py` gives about the data skew: no
     * single exponent holds across the range, so a curve is wrong somewhere and interpolation
     * through the measured points is wrong nowhere they were taken.
     */
    public static double shareAtRank(int rank) {
        if (rank < 1) {
            throw new IllegalArgumentException("rank starts at 1");
        }
        if (rank > ACTIVE_ORGANISATIONS) {
            return 0.0;
        }
        double[] first = MEASURED_SHARE[0];
        if (rank <= first[0]) {
            return first[1];
        }
        double[] last = MEASURED_SHARE[MEASURED_SHARE.length - 1];
        if (rank >= last[0]) {
            // **Past the last rank measured, decay to zero rather than hold flat.** Log-log cannot
            // reach zero, and the measurement puts rank 100 at 0.004% of device sync with the ranks
            // after it indistinguishable from nothing -- so a flat tail would hand the last ten
            // organisations the same share as the hundredth, which is the opposite of what was
            // seen. Linear to zero at the first silent rank: exact at the measured point, monotone,
            // and it stops where activity stops.
            double span = (ACTIVE_ORGANISATIONS + 1) - last[0];
            return last[1] * (1.0 - (rank - last[0]) / span);
        }
        for (int i = 0; i < MEASURED_SHARE.length - 1; i++) {
            double r0 = MEASURED_SHARE[i][0], s0 = MEASURED_SHARE[i][1];
            double r1 = MEASURED_SHARE[i + 1][0], s1 = MEASURED_SHARE[i + 1][1];
            if (r0 <= rank && rank <= r1) {
                double f = (Math.log(rank) - Math.log(r0)) / (Math.log(r1) - Math.log(r0));
                return Math.exp(Math.log(s0) + f * (Math.log(s1) - Math.log(s0)));
            }
        }
        return last[1];
    }

    /**
     * Weights for a feeder's rows, so drawing from it reproduces the measured concentration.
     *
     * Organisations are ranked by **how many users they contribute to the feeder**, not by name.
     * Co-tenant users scale with villages, which scale with subjects, so row count recovers the
     * dataset's own rank without this having to know how its organisations are named -- and it keeps
     * working if the co-tenant recipe is rebuilt at a different size.
     *
     * An organisation's share is then divided equally among its users, because the question the
     * measurement answers is how much of the platform's sync traffic the *organisation* produces.
     * Dividing by its user count rather than letting row count carry the weight a second time is
     * the difference between modelling the measured share and modelling its square.
     */
    public static Map<String, Double> rowWeights(List<Map<String, String>> rows,
                                                 String organisationColumn) {
        Map<String, List<Map<String, String>>> byOrg = new LinkedHashMap<>();
        for (Map<String, String> row : rows) {
            String org = row.get(organisationColumn);
            byOrg.computeIfAbsent(org == null ? "" : org, k -> new ArrayList<>()).add(row);
        }
        List<String> ranked = new ArrayList<>(byOrg.keySet());
        ranked.sort(Comparator.<String>comparingInt(o -> -byOrg.get(o).size()).thenComparing(o -> o));

        Map<String, Double> weights = new LinkedHashMap<>();
        for (int i = 0; i < ranked.size(); i++) {
            String org = ranked.get(i);
            List<Map<String, String>> users = byOrg.get(org);
            double share = shareAtRank(i + 1);
            double each = share / users.size();
            for (Map<String, String> u : users) {
                weights.put(key(u), each);
            }
        }
        return weights;
    }

    /**
     * Each organisation's rank in this feeder, by rows contributed. Same ordering `rowWeights`
     * uses, exposed because the media rate is a per-organisation measurement keyed the same way
     * and the two must not rank differently.
     */
    public static Map<String, Integer> ranks(List<Map<String, String>> rows,
                                             String organisationColumn) {
        Map<String, Integer> sizes = new LinkedHashMap<>();
        for (Map<String, String> row : rows) {
            String org = row.get(organisationColumn);
            sizes.merge(org == null ? "" : org, 1, Integer::sum);
        }
        List<String> ranked = new ArrayList<>(sizes.keySet());
        ranked.sort(Comparator.<String>comparingInt(o -> -sizes.get(o)).thenComparing(o -> o));
        Map<String, Integer> out = new LinkedHashMap<>();
        for (int i = 0; i < ranked.size(); i++) {
            out.put(ranked.get(i), i + 1);
        }
        return out;
    }

    /** Identity of a feeder row. `userName` is unique per user and is the column every mode reads. */
    public static String key(Map<String, String> row) {
        return row.get("userName");
    }

    /**
     * A feeder that draws rows in proportion to the measured shares.
     *
     * **Weighted draw rather than repeating rows in a `circular()` file.** Multiplicity would work
     * for the long-run proportions and would get the ordering wrong: `circular()` walks the file in
     * order, so an organisation holding 16% of the load would sync 16% of the time in a block and
     * not at all for the rest of the run. Production's busy tenants are busy throughout.
     *
     * Seeded, so two runs that differ in nothing else draw the same sequence.
     */
    public static java.util.Iterator<Map<String, Object>> feeder(List<Map<String, String>> rows,
                                                                 String organisationColumn,
                                                                 long seed) {
        Map<String, Double> weights = rowWeights(rows, organisationColumn);
        List<Map<String, String>> eligible = new ArrayList<>();
        List<Double> cumulative = new ArrayList<>();
        double running = 0;
        for (Map<String, String> row : rows) {
            double w = weights.getOrDefault(key(row), 0.0);
            if (w <= 0) {
                continue;   // an organisation past rank 110: holds rows, syncs nothing
            }
            running += w;
            eligible.add(row);
            cumulative.add(running);
        }
        if (eligible.isEmpty()) {
            throw new IllegalStateException(
                "no co-tenant user carries any measured sync share, so the feeder would never "
                + "produce a row. Check that the user file has an " + organisationColumn
                + " column -- without it every row falls into one organisation.");
        }
        final double total = running;
        final Random rng = new Random(seed);
        return new java.util.Iterator<Map<String, Object>>() {
            @Override public boolean hasNext() {
                return true;
            }
            @Override public Map<String, Object> next() {
                double x = rng.nextDouble() * total;
                int lo = 0, hi = cumulative.size() - 1;
                while (lo < hi) {
                    int mid = (lo + hi) >>> 1;
                    if (cumulative.get(mid) < x) {
                        lo = mid + 1;
                    } else {
                        hi = mid;
                    }
                }
                return new LinkedHashMap<>(eligible.get(lo));
            }
        };
    }

    /** How many organisations in this feeder will ever sync, and how many are present. */
    public static int[] coverage(List<Map<String, String>> rows, String organisationColumn) {
        Map<String, Double> weights = rowWeights(rows, organisationColumn);
        java.util.Set<String> active = new java.util.HashSet<>();
        java.util.Set<String> present = new java.util.HashSet<>();
        for (Map<String, String> row : rows) {
            String org = row.get(organisationColumn);
            present.add(org == null ? "" : org);
            if (weights.getOrDefault(key(row), 0.0) > 0) {
                active.add(org == null ? "" : org);
            }
        }
        return new int[]{active.size(), present.size()};
    }

    public static List<double[]> measuredShares() {
        List<double[]> out = new ArrayList<>();
        for (double[] p : MEASURED_SHARE) {
            out.add(new double[]{p[0], p[1]});
        }
        return Collections.unmodifiableList(out);
    }
}
