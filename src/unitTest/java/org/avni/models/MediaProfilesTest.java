package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/** What the measured media rates have to hold true, so they cannot collapse back to one constant. */
class MediaProfilesTest {

    @Test
    @DisplayName("the distribution reproduces production's aggregate")
    void theAggregateIsProductions() {
        // The whole point of normalising. Weighted by the same sync shares the co-tenant feeder
        // draws on, the per-rank rates must impose production's measured 0.2306 files per pushed
        // encounter -- not the 0.3153 the raw rates give under this weighting.
        double num = 0, den = 0;
        for (int rank = 1; rank <= CoTenantLoad.ACTIVE_ORGANISATIONS; rank++) {
            double share = CoTenantLoad.shareAtRank(rank);
            num += share * MediaProfiles.rateAtRank(rank);
            den += share;
        }
        assertEquals(MediaProfiles.PLATFORM_UPLOADS_PER_ENCOUNTER, num / den, 1e-6);
    }

    @Test
    @DisplayName("the aggregate is 10.8x the constant it replaces")
    void theOldConstantWasLow() {
        // 0.0214 was the share of program_encounter rows carrying any media, used as files per
        // row. If this ever drifts back toward it, the media path stops being exercised.
        assertEquals(10.8, MediaProfiles.PLATFORM_UPLOADS_PER_ENCOUNTER / 0.0214, 0.2);
    }

    @Test
    @DisplayName("normalisation records what it corrected rather than hiding it")
    void theUnnormalisedAggregateIsRecoverable() {
        // 0.3210 against the interpolated share curve the feeder draws on; 0.3153 against the
        // logs' exact per-organisation shares. The first is what the model would have imposed.
        assertEquals(0.3210, MediaProfiles.unnormalisedAggregate(), 0.001);
        assertEquals(1.39, MediaProfiles.unnormalisedAggregate()
                           / MediaProfiles.PLATFORM_UPLOADS_PER_ENCOUNTER, 0.01);
        assertTrue(MediaProfiles.normaliser() < 1.0,
            "the raw rates over-impose under sync-share weighting, so the normaliser scales down");
    }

    @Test
    @DisplayName("a rate measured at zero stays zero")
    void measuredZeroStaysZero() {
        // Rank 7 uploaded nothing in eleven days. Normalising multiplies, so zero survives -- and
        // it must, because that is the gate for a tenant whose forms cannot queue a file.
        assertEquals(0.0, MediaProfiles.rateAtRank(7));
    }

    @Test
    @DisplayName("the spread survives, because one constant was the defect")
    void theSpreadSurvives() {
        // 1.80 against a tail of 0.0012 is three orders of magnitude. Any change that flattens
        // this is the thing these replace.
        assertTrue(MediaProfiles.rateAtRank(1) / MediaProfiles.rateAtRank(2) > 100,
            "rank 1 should dwarf rank 2: " + MediaProfiles.rateAtRank(1) + " vs "
            + MediaProfiles.rateAtRank(2));
        assertTrue(MediaProfiles.rateAtRank(1) > 1.0, "the heaviest uploader should exceed a file "
            + "per encounter even after normalising");
    }

    @Test
    @DisplayName("unmeasured ranks get the tail rate, not zero and not the mean")
    void unmeasuredRanksGetTheTail() {
        double tail = MediaProfiles.rateAtRank(60);
        assertEquals(MediaProfiles.TAIL_RATE * MediaProfiles.normaliser(), tail, 1e-12);
        assertTrue(tail > 0, "a floor of zero would leave the whole tail unable to exercise media");
        assertTrue(tail < MediaProfiles.PLATFORM_UPLOADS_PER_ENCOUNTER / 10,
            "the tail is light; giving it the mean would invent an image-heavy platform");
    }

    @Test
    @DisplayName("a bundle with no media element gates to zero, whatever the rank")
    void theBundleGateWins() {
        // The one thing the bundle settles outright: a form with no media question cannot queue a
        // file however long the device is offline, and the measurement agrees to three decimals.
        assertEquals(0.0, MediaProfiles.fromBundleCapacity(0.0, 1));
        assertEquals(0.0, MediaProfiles.fromBundleCapacity(0.0, 60));
        // Above zero the capacity is a ceiling the realised rate exceeds, so the rank's measured
        // rate is used and the capacity is deliberately ignored rather than averaged in.
        assertEquals(MediaProfiles.rateAtRank(1), MediaProfiles.fromBundleCapacity(1.07, 1));
        assertEquals(MediaProfiles.rateAtRank(5), MediaProfiles.fromBundleCapacity(2.29, 5));
    }

    @Test
    @DisplayName("every rate is a plausible file count")
    void ratesArePlausible() {
        for (int rank = 1; rank <= CoTenantLoad.ACTIVE_ORGANISATIONS; rank++) {
            double r = MediaProfiles.rateAtRank(rank);
            assertTrue(r >= 0 && r < 10, "rank " + rank + " at " + r + " files/encounter");
        }
    }
}
