package org.avni.models;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Media files a co-tenant's encounter queues for upload, measured per organisation.
 *
 * **One constant stood where production has a 1,500-fold spread.** `CO_TENANT_MEDIA_PER_ENCOUNTER`
 * was 0.0214 for every tenant. Measured per organisation, the rate runs from 0.0007 to 1.80 files
 * per pushed encounter, and four of the nineteen organisations big enough to rate carry almost all
 * of it. The aggregate was wrong too: production uploads **0.2306 files per pushed encounter**
 * across the platform, so the single constant was 10.8x low.
 *
 * Where 0.0214 came from is worth recording, because it was not a mistake so much as a different
 * quantity: Q-analysis found 2.14% of `program_encounter` rows carry a media observation. Share of
 * rows carrying any media is only files per row if a media-bearing row carries exactly one file,
 * and it does not.
 *
 * **Upload only, deliberately.** `media/signedUrl` outnumbers `media/uploadUrl` 7.6 to 1 in the
 * same logs and is not modelled, because it is a download the user triggers on demand rather than
 * anything a sync does, and it is called by the web application and integrations as well as by the
 * app -- so its volume is not attributable to a device fleet. `uploadUrl` is clean by the same
 * test: **99.5% of its calls come from users that also pull entities**, which is to say from real
 * syncing devices.
 *
 * **What the bundle can and cannot say.** `survey_bundle` reports media files per filled form, and
 * for a bundle with no media elements that is zero and the measurement agrees exactly -- the
 * push-dominated archetype's bundle has none and it realises 0.0010. Above zero the bundle does not
 * predict the rate: the large pull-heavy archetype's bundle ceiling is 1.07 files per Encounter form
 * and it realises **1.80**, and repeating question groups do not explain it, since
 * `media_per_form_type` returns the same figures at one, two and three repeats for these bundles.
 * The reason is that **upload is asynchronous from the push**: files queue on the device and retry
 * until they succeed, so what a tenant transmits in an eleven-day window reflects queue drainage
 * and retries rather than form design. No bundle can supply that. So the bundle is a gate and a
 * ceiling, and the logs are the rate -- see {@link #fromBundleCapacity}.
 *
 * **The rates are normalised onto the measured aggregate rather than used raw.** Ranking here is by
 * share of device sync, which is what the co-tenant feeder draws on; production's aggregate is per
 * pushed encounter. The two weightings disagree, because the heaviest media uploader holds 16% of
 * sync and only 7.3% of encounter pushes -- so the raw rates under this weighting would impose
 * **0.3210 files per encounter against production's 0.2306, 1.39x**. Normalising keeps the measured
 * shape and the measured total; a rate measured at zero stays zero, which is the gate.
 *
 * That 0.3210 is computed against {@link CoTenantLoad#shareAtRank}, the curve the feeder actually
 * draws on, rather than against the exact per-organisation shares the logs give -- which put it at
 * 0.3153. The model's own weighting is the one worth correcting for, and the gap between the two
 * figures is the interpolation's, not a measurement's.
 *
 * Measured from `AuthenticationFilter` over 2026-09-10..19 and 09-28: 30,736 `uploadUrl` calls
 * against 133,259 pushed encounters. Organisations are referred to by rank; the mapping is local.
 */
public final class MediaProfiles {

    /** Production's own figure: `uploadUrl` calls per pushed encounter, platform-wide. */
    public static final double PLATFORM_UPLOADS_PER_ENCOUNTER = 0.2306;

    /**
     * Files per pushed encounter, by rank in share of device sync. As measured, before
     * normalisation.
     *
     * Rank 8 is absent on purpose: it made 6,794 upload calls against 226 pushed encounters, a
     * ratio of 30, because it uploads media without pushing encounters. An encounter-driven rate
     * cannot express that shape at all, so it takes the tail rate and the fact is recorded rather
     * than a meaningless 30 being encoded.
     */
    private static final Map<Integer, Double> MEASURED_BY_RANK = new LinkedHashMap<>();

    /**
     * Ranks nobody measured, and the median of the fifteen light ones that were.
     *
     * Not a floor of zero: most organisations do attach the occasional file, and zero would make
     * the whole tail incapable of exercising the media path at all.
     */
    public static final double TAIL_RATE = 0.0012;

    /** Applied to every measured rate so the aggregate lands on production's. */
    private static final double NORMALISER;

    static {
        Map<Integer, Double> m = MEASURED_BY_RANK;
        m.put(1, 1.8043); m.put(2, 0.0008); m.put(3, 0.0010); m.put(4, 0.0007);
        m.put(5, 0.0664);  m.put(6, 0.0023); m.put(7, 0.0000); m.put(9, 0.0027);
        m.put(10, 0.2478); m.put(11, 0.0081); m.put(12, 0.0153); m.put(13, 0.0054);
        m.put(14, 0.0089); m.put(15, 0.0012); m.put(16, 0.0008); m.put(17, 0.9747);
        m.put(18, 0.2174); m.put(19, 0.0008); m.put(20, 0.0012);

        // Weighted by the same sync shares the feeder draws on, so the normaliser corrects exactly
        // the weighting difference it exists to correct.
        double num = 0, den = 0;
        for (int rank = 1; rank <= CoTenantLoad.ACTIVE_ORGANISATIONS; rank++) {
            double share = CoTenantLoad.shareAtRank(rank);
            num += share * rawRateAtRank(rank);
            den += share;
        }
        double weightedMean = num / den;
        NORMALISER = weightedMean > 0 ? PLATFORM_UPLOADS_PER_ENCOUNTER / weightedMean : 1.0;
    }

    private MediaProfiles() {
    }

    private static double rawRateAtRank(int rank) {
        Double measured = MEASURED_BY_RANK.get(rank);
        return measured != null ? measured : TAIL_RATE;
    }

    /**
     * Files per pushed encounter for the organisation at this rank, normalised onto production's
     * aggregate. Zero where the measurement found zero.
     */
    public static double rateAtRank(int rank) {
        if (rank < 1) {
            throw new IllegalArgumentException("rank starts at 1");
        }
        return rawRateAtRank(rank) * NORMALISER;
    }

    /** What the raw rates would have imposed under this weighting, for the record. */
    public static double unnormalisedAggregate() {
        return PLATFORM_UPLOADS_PER_ENCOUNTER / NORMALISER;
    }

    public static double normaliser() {
        return NORMALISER;
    }

    /**
     * The gate: what to charge a tenant whose bundle `survey_bundle` has actually read.
     *
     * **Zero capacity means zero, and that is the one thing the bundle settles outright.** A form
     * with no media element cannot queue a file however long the device is offline, and the
     * measurement agrees to three decimal places. Above zero the capacity is a ceiling the realised
     * rate exceeds, for the asynchrony reason in this class's documentation, so the rank's measured
     * rate is used and the capacity is ignored rather than averaged in -- averaging a ceiling with a
     * rate would produce a number describing neither.
     */
    public static double fromBundleCapacity(double filesPerFilledForm, int rank) {
        if (filesPerFilledForm <= 0) {
            return 0.0;
        }
        return rateAtRank(rank);
    }
}
