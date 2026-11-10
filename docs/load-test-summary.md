# Load test summary: how many syncs an hour each server size handles

*A plain-language summary, 10 Nov 2026. The evidence behind each figure is in
[`findings-summary.md`](findings-summary.md) and [`execution-plan.md`](execution-plan.md).*

## Terms used

- **Sync:** one phone exchanging data with the server: sending new records and images, then downloading changes.
- **Daily sync:** a phone that has synced before, catching up.
- **Fresh sync:** a new or reset phone downloading its user's whole catchment.
- **vCPU:** a processor core. "16 + 16" means 16 cores on the app server and 16 on the database server.
- **Current release:** the server version in production during testing: 17.3, then 18.1. They performed the same; a side-by-side check gave the same cost per sync, and 18.1 changed nothing on the sync path. The "current release" rows were measured on 17.3.
- **Release 18.3:** the next version, with four performance fixes that roughly halve the server's work per sync:
  - removes a redundant database step run on every request;
  - stops records being needlessly re-saved;
  - loads less data when building sync responses;
  - lets the app request image-upload links in batches. This one needs the matching app update.
- **Holds:** no failed requests, and 95% of requests answered within 0.8 seconds.
- **Comfortable limit:** about 10% below the point where the server falls behind. This is the figure to plan on.

## Assumptions

- **Staff:** about 8 field workers per supervisor. A supervisor's catchment covers all their field workers' villages, about 8,400 beneficiaries. Supervisors download that whole catchment but don't record visits.
- **Area:** 3 field workers share a village of 3,000 beneficiaries, and each downloads the whole village: about 8,400 records with 6 months of visits.
- **Visits:** 10 per field worker per day on average, ranging from 5 to 23 in a sync.
- **History:** 6 months of past visits already on the server.
- **Images:** 8 per visit, about 500 KB each, sent one at a time over a 1 Mbps connection, about 4 seconds each.
- **Fresh syncs:** 1 in 100 syncs.
- **Timing, worst case:** every user syncs within the same hour, as at the start of a day. The same users spread over a normal day use about 2% of the server.
- **Other organisations:** 513 share the same server, syncing 792 times an hour, their busiest recorded hour.
- **Scope:**
  - Only sync is tested, with no web app, reports or bulk uploads running at the same time.
  - The users' data contains no programme enrolments.
  - The time a phone spends saving downloaded records is modelled on the app's SQLite storage. Phones still on the older Realm storage take 3–4× longer to save the same records.

## How long a sync takes on the phone

| User | Daily sync | Fresh sync (all 6 months) |
|---|---|---|
| Field worker | **~6 minutes**: ~5 uploading 80 images, ~40 seconds saving records, ~5 seconds on the server | **~1 minute**: nothing to upload, ~8,400 records |
| Supervisor | **~1.5–2 minutes**: no uploads, ~17,000–25,000 records to save | **~1.5–2 minutes**: the same records |

- **The test overstated daily syncs, because of a flaw in the simulation logic** ([`harness-pull-window.md`](harness-pull-window.md)).
  - The test downloaded each changed type of record from the start of its history, where the real app downloads only what changed since the last sync.
  - So a daily sync pulled about as much as a fresh sync: ~8,400 records for a field worker.
  - Real daily syncs are shorter than shown, mainly for supervisors, whose syncs are mostly saving records.
  - The server also did more work per sync than it will in practice, so **the capacity figures below are cautious**.
- These times hold across every server size tested, because the server is only 1–2% of a sync's time.
- What changes them far more is on the phone's side: a slow connection stretches the image uploads, and Realm storage stretches the saving, by 3–4×.

## Results

Sync counts are for the customer's users; the other organisations' 792 an hour run in addition.

| App cores | Database cores | Server version | Syncs per hour | Result |
|---|---|---|---|---|
| 2 | 2 | current release | ~1,700 | **fails**: hundreds of errors, slowest responses about 1 minute |
| 2 | 2 | release 18.3 | ~1,700 | holds |
| 8 | 8 | current release | 5,000 | holds, app server 62% busy |
| 16 | 16 | current release | 10,000 | holds, app server 59% busy; limit estimated at 14,000–16,000 |
| 16 | 16 | release 18.3 | **25,000 comfortable**, falls behind at ~27,500 | the app server is the limit |
| 32 | 16 | release 18.3 | **43,000 comfortable**, falls behind at ~48,000 | the database is the limit |
| 48 | 32 | release 18.3 | **50,000** holds; still keeping up at 70,000 | app server 55% busy, database 47%; limit estimated at ~90,000 |

- **Several smaller app servers work as well as one large one.** One 32-core server, two 16-core and four 8-core all did the same work for the same cost. Production can't run more than one app server yet; that needs separate changes.
- **Release 18.3 carries about 1.7× more syncs on the same hardware.**
