# What a simulated sync actually does

**One virtual user, start to finish.** The other documents describe pieces: the
[README](../README.md) documents each knob, [`sync-simulation-plan.md`](sync-simulation-plan.md)
§ D records where the harness and `SyncService.js` disagree and why, and
[`findings-d7.md`](findings-d7.md) measures the one part that is modelled rather than performed.
**This is the sequence they are pieces of**, for someone who needs to know what a run is doing
before reading any of them.

Source of truth is `AvniSyncSimulation.syncChainFor`. Where this and the code disagree, the code is
right and this is stale.

## The sequence

| | step | real request? | notes |
|---|---|---|---|
| 1 | **Draw a user** from the feeder | — | `circular()` for the customer, concentration-weighted for co-tenants |
| 2 | **Authenticate** | yes, or skipped | Cognito or none, per `AUTH_MODE` |
| 3 | **Bootstrap sync statuses** | yes, **once per user** | `POST /v2/syncDetails` with `[]` to learn what this user tracks |
| 4 | **Seed push identifiers** | yes, **once per user**, push only | pulls one page each of Individual, ProgramEnrolment, ProgramEncounter, Encounter to get real UUIDs to reference |
| 5 | **Decide the sync** | — | `fullSync` drawn **once per sync**, not per entity |
| 6 | **Push media** | `GET /media/uploadUrl` per file | the S3 `PUT` is **waited, not issued** |
| 7 | **Push data** | yes, per entity | `POST /encounters`, `/individuals`, … |
| 8 | **Reset-sync check** | yes | `GET /resetSyncs` |
| 9 | **Ask what changed** | yes | `POST /v2/syncDetails` with the **real** `entitySyncStatus` array |
| 10 | **Pull, entity by entity, page by page** | yes | with a **wait after every page** |
| 11 | **Post telemetry** | yes | `POST /syncTelemetry` |
| 12 | **Record the result** | — | one row in `sync-durations.csv` |

### Why push comes before pull

Because the client does it that way. `dataServerSync` runs `pushData`, then the reset-sync check,
then `getSyncDetails`. **The pull window's start is read from the server after the upload**, so a
device does not re-download what it just sent. Pushing after the pull would measure a different
system.

Within the push, **media goes first and completes before the first record**. `sync()` runs
`mediaSync` to completion before `dataServerSync`, and the two hit the same filter chain and
connection pool — interleaving them would spread a burst the real client delivers up front.

### Steps 3 and 4 are per user, not per sync

The bootstrap and the push seed run only the first time a given user appears in a run, and the
result is cached for the rest of it. They are setup, not part of the sync being measured — but
they do cost the server real requests, and they appear in the run's request counts.

## The three things that are modelled rather than performed

Everything above issues real HTTP against the server **except** these. Each is a deliberate trade,
and each is a reason a published number is not the whole truth.

### 1. The storage pause — 93% of a sync's duration

After each page is received, the virtual user **waits** for as long as the device would have spent
parsing and writing those records. No request is made; the clock advances.

This is the single largest component of any duration this suite reports. The rates come from
`StorageProfiles`, measured per entity from production's own server logs (11 days, 1.88M requests,
24,667 confirmed full pages, via `tools/inter_request_gap.py`), with `BASE_MS_PER_RECORD` as a
fallback for entities the logs did not reach.

> **[D7](findings-d7.md) measured a real device and the model is SQLite-shaped.** 2.22–2.53
> ms/record on SQLite against 10.18–11.37 on Realm. **Every duration published by this suite is
> about right for a SQLite fleet and understates a Realm one by roughly three times**, and a
> supervisor on Realm waits nine minutes for one sync. The server side is unaffected: `serverMs` is
> measured, not modelled.

### 2. The S3 upload — bytes not sent, time still spent

Each queued media file costs a real `GET /media/uploadUrl` against the server, and then a **pause**
for how long the `PUT` would take. The bytes never leave the injector.

**500 KB per file at 125 KB/s, so a flat 4 seconds each, serial** — `1000 × fileKb / uploadKbps`.

| | default | where it comes from |
|---|---|---|
| `MEDIA_FILE_KB` | **500** | the client captures 1280×960 at quality 1 (`MediaV2FormElement`), a full-quality 1.2 MP JPEG. **Audio and video are larger**, so this understates them. |
| `MEDIA_UPLOAD_KBPS` | **125** | about 1 Mbps — "optimistic for rural 3G, pessimistic for a town on 4G" |
| `PUSH_MEDIA_PER_ENCOUNTER` | **1.42** | **a default the code tells you not to trust** — "set it from the deployment", via `make survey_bundle`. Production averages 0.23 per pushed encounter; the customer's screening bundle reaches **16 on one**, which the code's own table puts at 1,408 s of transfer per sync. |

> **Both are assumptions, not measurements.** Unlike `StorageProfiles`, which came from 11 days of
> production logs, neither was derived from anything observed. **And `MEDIA_UPLOAD_KBPS` has never
> been swept**, though the code comment says to — it is the single biggest lever on how long a
> media-bearing sync takes, moving a 31-file sync from 26 s to 402 s across the documented range.
> Every run so far used 125.

S3 serves those objects directly, so a `PUT` from the injector would measure an in-region pipe
moving 500 KB in tens of milliseconds, where a field device on rural 3G takes four seconds —
neither the server's load nor the device's timing. Serial, because `PARALLEL_UPLOAD_COUNT` is 1 in
`MediaQueueService`.

**This inflates sync duration without adding server load.** During the transfer the device asks
avni-server for nothing, so syncs-in-progress rises several-fold while requests-in-flight does not
move.

### 3. Media *pull* — not simulated, and correctly so

Images are fetched on demand when viewed, not during a sync. There is nothing to model.

## What the pull actually iterates

Step 10 is two nested loops, and the shape matters for reading request counts:

```
for each entity the server said has changed            (from step 9's response)
    for each (entityType) the server listed for it
        GET page 0, 1, 2 … until a short page
            wait for the modelled storage cost of that page
```

So **requests per sync is a function of records and `PAGE_SIZE`**, not of the entity count. A field
worker makes about 17; a supervisor at span 8.4 makes 38.6; a supervisor at span 20 makes more
again. `PAGE_SIZE` is 1000, matching the client.

Entities the server reports as unchanged are not requested at all — which is the whole purpose of
step 9, and why `syncDetails` is expensive on the server side.

## What varies between runs

| knob | what it changes |
|---|---|
| `SYNC_MODE` | `full`, `incremental`, `realistic` (per-user gaps drawn from production's measured distribution), `csv` |
| `PUSH` | whether steps 4, 6 and 7 happen at all |
| the feeder | which cohort syncs — role mix and tenant mix are a property of **file order**, since the feeder is circular and a run consumes a prefix |
| injection profile | `burst` or `steady`, and the arrival window |
| `CO_TENANTS` | whether production's other organisations sync alongside, drawn by measured concentration rather than evenly |
| the dataset | what is there to pull; the span of a supervisor's catchment is a **dataset**, not a flag |

### The defaults, as the code ships them

Every one is `-D`-overridable and every one is recorded in the run's `run-metadata.json`, so a past
run can be checked rather than assumed.

| | default | |
|---|---|---|
| `SYNC_MODE` | `csv` | runs use `realistic`, `full` or `incremental`; `csv` reads the window from the feeder |
| `SYNC_WINDOW_HOURS` | `12` | the assumed working-day plateau — **the assumption cases 11–13 exist to test** |
| `FULL_SYNC_PERCENT` | `1.0` | one sync in a hundred draws a full pull |
| `INCREMENTAL_SINCE_HOURS` | `24` | only for `SYNC_MODE=incremental` |
| `PAGE_SIZE` | `1000` | matches the client |
| `PUSH` | `false` | off in most runs |
| `CO_TENANTS` | `false` | |
| `CO_TENANT_SYNCS_PER_HOUR` | `792` | production's busiest recorded hour |
| `PUSH_PROFILE` / `STORAGE_PROFILE` | `customer` | the three organisations that agree, at 79% of the sample; `production` is the pooled figure |
| `STORAGE_MODEL` | `weighted` | per-entity rates from `StorageProfiles`; `none` charges nothing |
| `BASE_MS_PER_RECORD` | `2.78` | **fallback only**, for entities the production logs did not reach |
| `MS_PER_PAGE` | `112` | fixed per-page client cost, **measured and net of network** — 174 observed minus this environment's 62 ms median request, so the simulation does not charge the round trip twice |
| `MAX_STORAGE_PAUSE_MS` | `30000` | a cap that should never bind; if it does, the model is wrong |
| `MEDIA_MODEL` | `pause` | `none` charges nothing for media |
| `PROFILE` | `ramp` | or `burst` / `steady` |
| `BURST_SECONDS` | `60` | |
| `DURATION_MINUTES` | `120` | |
| `AUTH_MODE` | `none` | Cognito otherwise |
| `MAX_FAILED_PERCENT` / `MAX_P95_MS` | `0.05` / unset | the gates a run is judged against |

## Things people get wrong about it

**"Devices in flight" is not the cohort size.** Arrivals are open — independent of service time — so
`in flight = arrival rate × service time`, where the arrival rate is **syncs actually performed**,
not users configured. Compressing the window raises concurrency, not throughput.

**A full sync is not the expensive outlier.** An incremental sync pulls 69% of what a full one
pulls, because `realistic` draws per-user gaps from a heavy-tailed distribution — real devices
often have not synced for weeks.

**Every virtual user is a p50 device.** `StorageProfiles` reproduces the median and none of the
spread — `encounter` runs p50 6.4, p90 55, p99 168 ms/record in production. Arrivals are more
regular than production's, so contention at a given concurrency is **understated**.

**Catchments are uniform.** The generator gives every village identical volume, so case 14's 63
full syncs pulled *exactly* 15,732 records each. The mean is sound; the spread is an artefact, and
the tail — what the worst catchment costs — is unanswered.

**Program data is absent from the customer cohort.** `program_enrolment` and `program_encounter`
are 0 rows in the ten pilot tenants, so every customer sync measured is smaller than a real one.
The co-tenants do carry them, 2.41 M rows, so the server path is exercised — just not by a customer
sync.

## Where to go next

* **Each knob, and its default** — [README](../README.md): *Sync window*, *Client-side storage
  cost*, *The push path*, *Media*, *Injection profiles*
* **Why the harness differs from the client** — [`sync-simulation-plan.md`](sync-simulation-plan.md)
  § D, and § D6/D7 for the storage model's derivation
* **What the storage model is worth** — [`findings-d7.md`](findings-d7.md)
* **What the runs found** — [`findings-summary.md`](findings-summary.md)
* **The run ritual itself** — [`sync-simulation-plan.md`](sync-simulation-plan.md) § G
