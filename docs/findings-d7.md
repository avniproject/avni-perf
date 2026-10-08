# D7 — what storage actually costs, 8 October 2026

Every sync duration this suite has published is 93–94% `pausedMs`: a *modelled*
number, computed from records pulled using `baseMsPerRecord`, which
`StorageProfiles` describes as "derived from the ceiling rather than measured — a
deliberate upper bound". Case 14's 80 s and case 3's 223 s rest on it entirely.

D7 measures it. Four syncs from one handset against the loaded `pilot-day-180`,
two users per storage engine, same server, same dataset, six minutes apart.
`avni-client` records `networkMs`, `parseMs` and `persistMs` per entity per page
in `sync_telemetry.entity_status`, so the figure is
`(parseMs + persistMs) / records` — network excluded deliberately, because the
simulation pays network and server for real and folding them in is the
double-count the `baseMsPerRecord` comment attributes to Q1.

## The answer

**The model is sound in shape and wrong in magnitude, and which engine you run
decides by how much.**

| user | role | engine | records | persist | **ms/record** | whole sync |
|---|---|---|---|---|---|---|
| `u201000001` | field worker | realm | 15,734 | 159.4 s | **10.183** | 192.1 s |
| `u201000002` | field worker | sqlite | 15,750 | 34.3 s | **2.220** | 67.6 s |
| `u201000502` | supervisor | realm | 43,293 | 490.4 s | **11.369** | **537.1 s** |
| `u201000503` | supervisor | sqlite | 43,314 | 107.9 s | **2.529** | 159.5 s |

`baseMsPerRecord` is **2.78**. That is SQLite's number — within 25% of the
measured 2.22–2.53 — and **3.7–4.1× optimistic for Realm**. On Realm it is not an
upper bound at all; it is a floor.

**A supervisor on Realm waits nine minutes** for one sync.

## Linear in records, which is the part the model got right

ms/record barely moves across a 2.75× increase in volume: Realm 10.18 → 11.37,
SQLite 2.22 → 2.53. The Realm/SQLite ratio holds too, 4.6× then 4.5×.

So modelling storage as linear in records is justified. The constant is wrong,
not the shape — which means the published figures can be rescaled rather than
rerun.

## But one constant hides a large per-entity spread

| entity | realm | sqlite |
|---|---|---|
| Encounter | 13.1 → 13.7 | 2.46 → 2.76 |
| Individual | 4.9 → 5.0 | 1.72 → 1.85 |

Encounter costs **2.7× Individual** on Realm and 1.5× on SQLite. Encounter also
dominates the record count — 10,778 of 15,734 for a field worker, 32,334 of
43,293 for a supervisor — so a single blended constant misprices any sync whose
composition differs from the one it was fitted to. A per-entity profile would be
the honest next step.

## What this does to everything already published

| | harness modelled | real SQLite | real Realm |
|---|---|---|---|
| case 14, full sync | 80.1 s | 67.6 s | **192.1 s** |
| case 3, largest supervisor | 223.4 s | 159.5 s | **537.1 s** |

The harness models something close to a SQLite device. **Every duration quoted so
far is about right for a SQLite fleet and understates a Realm one by 2.4–3.4×.**

The server side is unaffected: `serverMs` was 6–7% in every case and is measured,
not modelled. What changes is the user-facing total, which is the number anyone
outside this exercise actually cares about.

## What this is not

* **One device.** A motorola handset, `isEmulator: false`. Not a fleet, not a
  range of hardware, and nothing here says how a cheaper phone behaves.
* **Both engines ran in low power mode**, unplugged, battery 52–53%. The absolute
  numbers are therefore pessimistic. The *ratio* is not: both syncs were equally
  penalised, six minutes apart, same device, same network.
* **Pull only.** `PUSH` was off, as it is throughout.
* **Four syncs.** Enough to establish a ratio and a per-record constant; not
  enough for a distribution.

## What to do next

* **Decide which engine the fleet is on**, because that single fact changes every
  published duration by a factor of three. `computeDesiredBackend()` returns
  SQLite only for the "SQLite Migration" group, so today the answer is per user.
* **Rescale rather than re-run.** Storage is linear in records, so case 2, 3, 4
  and 14 can be restated for Realm without touching the environment.
* **Replace the single constant with a per-entity profile.** Encounter at 13.7 and
  Individual at 5.0 are different enough that blending them loses the thing being
  modelled.
* **Measure a second device** before quoting absolutes, and one not in low power
  mode.
