package org.avni.models;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

/**
 * What the measured per-entity rates have to hold true, so they cannot drift back into a single
 * number or be applied the wrong way round.
 */
class StorageProfilesTest {

    @Test
    @DisplayName("the observation-bearing entities do not all cost the same")
    void theObservationEntitiesDiffer() {
        // The defect these replace: one uniform weight of 3.0 charged all four 8.34 ms/record,
        // and that figure landed on programEncounter -- production's largest table, and the one
        // these scenarios never write.
        double lo = Double.MAX_VALUE, hi = 0;
        for (String e : new String[]{"individual", "encounter", "programEncounter",
                                     "programEnrolment"}) {
            double v = StorageProfiles.CUSTOMER.get(e);
            lo = Math.min(lo, v);
            hi = Math.max(hi, v);
        }
        assertTrue(hi / lo > 1.5, "a uniform weight cannot express a " + (hi / lo) + "x range");
    }

    @Test
    @DisplayName("production is never cheaper than the customer's own deployment")
    void productionIsNotCheaper() {
        // The customer's figure is three agreeing organisations; the platform includes a tail
        // running ten to twenty times slower. Production cheaper anywhere means the two profiles
        // were swapped, which would quietly reverse the point of having them.
        StorageProfiles.CUSTOMER.forEach((entity, customer) -> {
            Double production = StorageProfiles.PRODUCTION.get(entity);
            assertNotNull(production, entity + " is missing from the production profile");
            assertTrue(customer <= production + 0.001,
                entity + ": customer " + customer + " exceeds production " + production);
        });
    }

    @Test
    @DisplayName("both profiles cover every entity the datasets generate")
    void bothCoverTheGeneratedEntities() {
        for (String e : new String[]{"individual", "encounter", "programEnrolment",
                                     "programEncounter"}) {
            assertTrue(StorageProfiles.CUSTOMER.containsKey(e), e + " unmeasured in customer");
            assertTrue(StorageProfiles.PRODUCTION.containsKey(e), e + " unmeasured in production");
        }
    }

    @Test
    @DisplayName("the default is the customer's own deployment, as PUSH_PROFILE's is")
    void theDefaultIsTheCustomers() {
        assertSame(StorageProfiles.CUSTOMER, StorageProfiles.byName("customer"));
        assertSame(StorageProfiles.CUSTOMER, StorageProfiles.byName("anything-else"));
        assertSame(StorageProfiles.CUSTOMER, StorageProfiles.byName(null));
        assertSame(StorageProfiles.PRODUCTION, StorageProfiles.byName("PRODUCTION"));
    }

    @Test
    @DisplayName("every rate is plausible client work rather than a stray server figure")
    void theRatesArePlausible() {
        StorageProfiles.PRODUCTION.forEach((entity, ms) -> assertTrue(ms > 0.1 && ms < 60,
            entity + " at " + ms + " ms/record is not client work"));
    }
}
