package org.avni.models;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * How a device asks for presigned upload URLs: one per file, or in batches.
 *
 * **0 is today's client.** `MediaQueueService` calls `GET /media/uploadUrl/{fileName}` once per
 * queued file, and each call pays the server's per-request overhead -- about twelve database
 * statements for a signature that needs none (avniproject/avni-server#1100).
 *
 * **1 to 50 is the batched client** of avniproject/avni-client#2218. It takes the next group of at
 * most N queued files, gets all their URLs from one `POST /media/uploadUrls`, then uploads the
 * group one file at a time as before. 50 is the server's own cap
 * (`MediaController.MAX_UPLOAD_URLS_PER_REQUEST`), which answers a 51st name with a 400, so a
 * larger setting is refused here rather than turned into a run full of failures.
 *
 * The URL expiry does not bind at any allowed size: upload URLs live ten minutes, and fifty files
 * at the default 4 s each take 200 s.
 */
public final class UploadUrlBatching {

    /** avni-server's `MediaController.MAX_UPLOAD_URLS_PER_REQUEST`. */
    public static final int MAX_PER_REQUEST = 50;

    private UploadUrlBatching() {
    }

    /** `UPLOAD_URL_BATCH`: blank or 0 is the per-file client; 1..50 the batched one. */
    public static int parse(String raw) {
        if (raw == null || raw.isBlank()) {
            return 0;
        }
        int batch;
        try {
            batch = Integer.parseInt(raw.trim());
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("UPLOAD_URL_BATCH must be a whole number, got '" + raw + "'");
        }
        if (batch < 0 || batch > MAX_PER_REQUEST) {
            throw new IllegalArgumentException("UPLOAD_URL_BATCH must be 0 (one GET per file) or 1.."
                + MAX_PER_REQUEST + " (files per POST /media/uploadUrls, the server's cap), got " + batch);
        }
        return batch;
    }

    /**
     * The group sizes a device holding `files` queued files requests in: full groups of `batch`,
     * then the remainder. Empty when there is nothing to upload or batching is off.
     */
    public static List<Integer> groups(int files, int batch) {
        if (files <= 0 || batch <= 0) {
            return Collections.emptyList();
        }
        List<Integer> groups = new ArrayList<>((files + batch - 1) / batch);
        for (int left = files; left > 0; left -= batch) {
            groups.add(Math.min(batch, left));
        }
        return groups;
    }

    /** Requests a sync with `files` uploads makes for its URLs: one per file, or one per group. */
    public static int requests(int files, int batch) {
        if (files <= 0) {
            return 0;
        }
        return batch <= 0 ? files : (files + batch - 1) / batch;
    }
}
