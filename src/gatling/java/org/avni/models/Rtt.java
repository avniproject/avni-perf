package org.avni.models;

import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Round-trip time from the injector to the target, summarised for the run archive.
 *
 * **Why it is recorded at all.** A sync is about 109 requests, so every millisecond of round trip
 * is paid 109 times: 25 ms adds 2.7 s to a 14.1 s median. That is a constant offset on every
 * result, not noise that averages out, and it is the reason two runs from different injector
 * positions cannot be compared. Recording the label and the hostname said *that* the position
 * differed; this says *by how much*.
 *
 * **Measured as a bare TCP connect, not as a request.** A handshake is one round trip with no
 * application involvement, so it isolates the network from whatever the server is doing. An HTTP
 * call to `/ping` would fold in server time, and a TLS handshake adds further round trips.
 *
 * **Both the floor and the typical value are kept.** The minimum is the cleanest estimate of the
 * network itself, with the least queuing; the median is closer to what the run will actually pay.
 * They diverge on a congested or shared path, and that divergence is itself worth seeing.
 */
public final class Rtt {

    /** What a run records when the target could not be reached at all. */
    public static final Rtt UNMEASURED = new Rtt(List.of(), 0);

    private final List<Double> samples;
    private final int attempts;

    public Rtt(List<Double> samples, int attempts) {
        List<Double> sorted = new ArrayList<>(samples);
        Collections.sort(sorted);
        this.samples = Collections.unmodifiableList(sorted);
        this.attempts = attempts;
    }

    public boolean measured() {
        return !samples.isEmpty();
    }

    public double minMillis() {
        return samples.isEmpty() ? -1 : samples.get(0);
    }

    public double medianMillis() {
        if (samples.isEmpty()) {
            return -1;
        }
        int n = samples.size();
        return n % 2 == 1
            ? samples.get(n / 2)
            : (samples.get(n / 2 - 1) + samples.get(n / 2)) / 2.0;
    }

    /**
     * What one sync pays for the network alone, at the median: 109 requests, each one round trip.
     *
     * An estimate rather than a measurement — it assumes a connection per request, which keep-alive
     * makes pessimistic, and ignores that some requests carry enough body to cost more than one
     * round trip. It is here to make the number legible: 4 ms and 40 ms are both "small" until
     * multiplied by 109.
     */
    public double syncOverheadSeconds(int requestsPerSync) {
        return measured() ? medianMillis() * requestsPerSync / 1000.0 : -1;
    }

    public Map<String, Object> asMetadata(int requestsPerSync) {
        Map<String, Object> m = new LinkedHashMap<>();
        if (!measured()) {
            m.put("status", attempts == 0
                ? "not attempted"
                : "unreachable - " + attempts + " attempts, none connected");
            return m;
        }
        m.put("minMillis", round(minMillis()));
        m.put("medianMillis", round(medianMillis()));
        m.put("samples", samples.size());
        m.put("attempts", attempts);
        m.put("estimatedSyncOverheadSeconds", round(syncOverheadSeconds(requestsPerSync)));
        m.put("basis", "TCP connect, minimum is the floor and median what a run pays");
        return m;
    }

    private static double round(double v) {
        return Math.round(v * 100.0) / 100.0;
    }
}
