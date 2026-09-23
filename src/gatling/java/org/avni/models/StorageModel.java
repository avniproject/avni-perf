package org.avni.models;

/**
 * What a page of records costs the client, as a pause the simulation takes after fetching it.
 *
 * ```
 * pause = min(maxMillis, msPerPage + records x weight x msPerRecord)
 * ```
 *
 * **The per-page term is a floor, not a ceiling**, which is the easy thing to misread: it is added
 * to every page whatever its size, and the per-record term accumulates on top. At the default
 * 174 ms and 0.60 ms/record the two are equal at about 290 records on a 1x entity; below that the
 * fixed term dominates and above it the per-record term does.
 *
 * **What bounds it above is `maxMillis`, and it is a guard rather than the mechanism.** Once a cap
 * binds, page size stops changing the pause, and the relationship between volume and duration is
 * precisely what D6 exists to model and F7 exists to fit. The per-record default is therefore
 * chosen so the heaviest page a device can pull — 1000 records on a 3x entity — lands just under
 * the cap rather than being clipped by it.
 *
 * Lives here rather than on the simulation so the arithmetic is testable without the simulation's
 * static initialisation, which loads the entity table and the user file.
 */
public final class StorageModel {

    private StorageModel() {
    }

    public static long pauseMillis(double msPerPage, int records, double weight,
                                   double msPerRecord, double maxMillis) {
        return clamp(msPerPage + records * weight * msPerRecord, maxMillis);
    }

    /** Clamped into [0, maxMillis]. Zero is reachable by netting the server's response time out
     *  of `msPerPage`, which the simulation's comments recommend, on a page that returned nothing. */
    public static long clamp(double millis, double maxMillis) {
        return Math.round(Math.max(0.0, Math.min(millis, maxMillis)));
    }
}
