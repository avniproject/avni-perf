package org.avni.models;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ThreadLocalRandom;

/**
 * How many records of one entity a single sync pushes, drawn from production's own distribution.
 *
 * The first version of D3 used a fixed count per sync - 20 program encounters, derived from "20
 * encounters per worker per day". Q17 measured the real thing across 30 days of `sync_telemetry`
 * and the fixed model was wrong twice over:
 *
 * **Most syncs push nothing of a given entity.** Program encounters appear in 28% of syncs,
 * subjects in 58%, general encounters in 21%. Pushing on every sync overstated the write path by
 * roughly the reciprocal.
 *
 * **And the volume is heavily skewed.** Program encounters run p50 3, p95 33, max 323. A mean
 * alone would miss both ends: the median sync that pushes three records, and the rare one that
 * pushes hundreds - serially, one POST each.
 *
 * So a draw is two steps: does this sync push this entity at all, and if so how many.
 */
public class PushVolume {
    public final String entityName;
    /** Share of syncs that push at least one of these. */
    public final double probability;
    /**
     * Fewest records a pushing sync carries.
     *
     * One for production, where the median sync pushes one or three records and a sync carrying a
     * single row is ordinary. Not one for a projected workload: a worker doing twenty encounters a
     * day does not have days with one, and leaving the floor at one drags the modelled mean so far
     * below the stated figure that no tail can lift it back.
     */
    public final int min;
    public final int p50;
    public final int p95;
    public final int max;
    /** Mean conditional on pushing. Used to fit the tail - see tailExponent. */
    public final double mean;

    private final double tailExponent;

    /**
     * Anything this instance had to correct or could not honour.
     *
     * These used to happen in silence. A typo in a `-DPUSH_*` override produced a different
     * distribution from the one asked for and said nothing, which in a repository that has twice
     * been bitten by silent defaults is the wrong default behaviour. Read and printed at startup
     * by the simulation, so a bad override is visible in the same place as everything else that
     * shapes a run.
     */
    public final List<String> warnings = new ArrayList<>();

    public PushVolume(String entityName, double probability, int p50, int p95, int max, double mean) {
        this(entityName, probability, 1, p50, p95, max, mean);
    }

    public PushVolume(String entityName, double probability, int min, int p50, int p95, int max,
                      double mean) {
        this.entityName = entityName;
        if (probability < 0 || probability > 1) {
            throw new IllegalArgumentException("Push volume for " + entityName
                + ": probability must be between 0 and 1, got " + probability
                + ". Above 1 makes every sync push this entity and below 0 makes none, so it is a"
                + " typo rather than an intent.");
        }
        this.probability = probability;
        this.min = Math.max(1, min);
        this.p50 = Math.max(this.min, p50);
        this.p95 = Math.max(this.p50, p95);
        this.max = Math.max(this.p95, max);
        this.mean = mean;
        if (this.min != min) {
            warnings.add(clamped("min", min, this.min));
        }
        if (this.p50 != p50) {
            warnings.add(clamped("p50", p50, this.p50));
        }
        if (this.p95 != p95) {
            warnings.add(clamped("p95", p95, this.p95));
        }
        if (this.max != max) {
            warnings.add(clamped("max", max, this.max));
        }
        this.tailExponent = fitTail();
    }

    private String clamped(String name, int given, int used) {
        return String.format(
            "%s: %s was given as %d and raised to %d - the quantiles have to be non-decreasing, so"
                + " this is not the distribution that was asked for",
            entityName, name, given, used);
    }

    /**
     * A draw for one sync: zero when this sync pushes none of this entity.
     */
    public int draw() {
        ThreadLocalRandom rng = ThreadLocalRandom.current();
        if (rng.nextDouble() >= probability) {
            return 0;
        }
        return quantile(rng.nextDouble());
    }

    /**
     * Inverse CDF in three log-linear segments: 1 to p50 over the bottom half, p50 to p95 over the
     * next 45%, p95 to max over the last 5%.
     *
     * Log-linear rather than linear because the distribution spans two orders of magnitude, and a
     * linear interpolation between p50 3 and p95 33 would put far too much mass in the twenties.
     *
     * The top segment is reshaped by `tailExponent` so that the whole distribution reproduces the
     * measured mean as well as the two percentiles. Without it the 5% band between p95 and max
     * carries so much weight on its own that the mean comes out two to three times high.
     */
    public int quantile(double u) {
        double lo, hi, f;
        if (u <= 0.5) {
            lo = min; hi = p50; f = u / 0.5;
        } else if (u <= 0.95) {
            lo = p50; hi = p95; f = (u - 0.5) / 0.45;
        } else {
            lo = p95; hi = max; f = Math.pow((u - 0.95) / 0.05, tailExponent);
        }
        if (hi <= lo) {
            return (int) Math.max(1, lo);
        }
        return (int) Math.max(1, Math.round(Math.exp(Math.log(lo) + f * (Math.log(hi) - Math.log(lo)))));
    }

    /**
     * Solve for the tail shape that makes the modelled mean match the measured one.
     *
     * Analytic rather than sampled, so the table is identical on every run and every injector. The
     * first two segments have a closed-form mean; only the reshaped tail needs integrating, and a
     * thousand-point trapezoid is far more precision than four input statistics deserve.
     */
    private double fitTail() {
        if (max <= p95 || mean <= 0) {
            return 1.0;
        }
        double lo = 1.0, hi = 1.0e4;
        // modelMean decreases in k: a larger exponent pushes the tail's mass back towards p95.
        // Both ends of the bracket are therefore reachable failures, and both are reported.
        //
        // A very large exponent pins the tail at p95. If even that overshoots the measured mean,
        // the inputs are inconsistent - report the flattest tail rather than diverging.
        if (modelMean(hi) > mean) {
            warnings.add(String.format(
                "%s: mean %.2f is below what min/p50/p95/max can produce even with the tail pinned"
                    + " at p95 (lowest reachable %.2f). Draws will average high.",
                entityName, mean, modelMean(hi)));
            return hi;
        }
        // And the other direction, which used to pass in silence: with the fattest tail the model
        // still cannot reach the stated mean, so the search converges at k=1 and the distribution
        // quietly averages low. Reachable by asking for a mean above max.
        if (modelMean(lo) < mean) {
            warnings.add(String.format(
                "%s: mean %.2f is above what min/p50/p95/max can produce even with the fattest"
                    + " tail (highest reachable %.2f). Draws will average low.",
                entityName, mean, modelMean(lo)));
            return lo;
        }
        for (int i = 0; i < 60; i++) {
            double mid = Math.sqrt(lo * hi);
            if (modelMean(mid) > mean) {
                lo = mid;
            } else {
                hi = mid;
            }
        }
        return Math.sqrt(lo * hi);
    }

    private double modelMean(double k) {
        return 0.5 * logUniformMean(min, p50) + 0.45 * logUniformMean(p50, p95)
            + 0.05 * reshapedTailMean(k);
    }

    /** E[lo * (hi/lo)^f] for f uniform on [0,1]. */
    private static double logUniformMean(double lo, double hi) {
        if (hi <= lo) {
            return lo;
        }
        double r = Math.log(hi / lo);
        return lo * (Math.exp(r) - 1) / r;
    }

    private double reshapedTailMean(double k) {
        double r = Math.log((double) max / p95);
        int n = 1000;
        double sum = 0;
        for (int i = 0; i <= n; i++) {
            double g = (double) i / n;
            double w = (i == 0 || i == n) ? 0.5 : 1.0;
            sum += w * p95 * Math.exp(r * Math.pow(g, k));
        }
        return sum / n;
    }

    /** Records per sync averaged over all syncs, including those that push none. */
    public double perSync() {
        return probability * mean;
    }

    /**
     * Overridden from a system property, "probability:p50:p95:max:mean" or
     * "probability:min:p50:p95:max:mean".
     */
    public static PushVolume parse(String entityName, String spec, PushVolume fallback) {
        if (spec == null || spec.isEmpty()) {
            return fallback;
        }
        String[] p = spec.split(":");
        if (p.length == 5) {
            return new PushVolume(entityName, Double.parseDouble(p[0]), Integer.parseInt(p[1]),
                Integer.parseInt(p[2]), Integer.parseInt(p[3]), Double.parseDouble(p[4]));
        }
        if (p.length == 6) {
            return new PushVolume(entityName, Double.parseDouble(p[0]), Integer.parseInt(p[1]),
                Integer.parseInt(p[2]), Integer.parseInt(p[3]), Integer.parseInt(p[4]),
                Double.parseDouble(p[5]));
        }
        throw new IllegalArgumentException("Push volume for " + entityName
            + " must be probability:p50:p95:max:mean or probability:min:p50:p95:max:mean, got " + spec);
    }
}
