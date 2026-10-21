# Sizing the hour that worries us: 1,500 workers, media-heavy, co-tenants live

**The question is not "does it work" but "what would it take".** Every run so far has measured a
server that was either comfortable or broken. This sizes a load nobody has run, from quantities
that have been measured, and says what it would need.

**Nothing here is a measurement of this scenario.** It is arithmetic over measured inputs, each
named below with where it came from, so that when the run happens the estimate can be scored
rather than quietly forgotten.

## The scenario

| | |
|---|---|
| customer users | **1,500**, arriving over **1 hour** |
| push | **on** |
| media | **8 images per encounter** — the customer's screening bundle, not the platform average |
| co-tenants | syncing at **792 syncs/hour**, production's busiest recorded hour |
| dataset | `pilot-day-180` shape, co-tenants present and active |

## The inputs, and where each comes from

| input | value | source |
|---|---|---|
| encounters per worker per day | **20** | **the customer's own projection**, used as the median — `AvniSyncSimulation:1038`, and the figure every recipe carries |
| media files per sync | **160** | 20 × 8 |
| media file size | 500 KB | `MEDIA_FILE_KB` — 1280×960 quality-1 JPEG; audio and video are larger |
| upload bandwidth | 125 KB/s | `MEDIA_UPLOAD_KBPS`, about 1 Mbps |
| requests per sync today | 87.9 | case 11 run 1: 143,211 requests over 1,630 syncs, with ~33 media calls |
| CPU per push sync today | **4.94 s** | case 11 run 1, from `apm.service.cpu.usertime` |
| CPU per co-tenant sync | **1.68 s** | case 7 minus case 6's customer rate, over 1,584 co-tenant syncs |
| CPU per `uploadUrl` | **~8 ms** | **inferred, not measured** — 11.7 ms wall minus 5.3 ms database, case 11 pair C |

## What it comes to

**Requests**

```
per sync      87.9 − 33 (today's media) + 160  =  ~215
per hour      1,500 × 215                      =  322,500  →  ~90 rps
```

Case 1 put the knee between **57 and 72 rps** on 2 vCPU. **This is roughly 1.3× past it.**

**CPU**

| | CPU s |
|---|---|
| customer sync today | 4.94 |
| plus 127 extra `uploadUrl` at ~8 ms | +1.02 |
| **per customer sync** | **~5.96** |
| × 1,500 | 8,940 |
| co-tenants, 792 × 1.68 | +1,331 |
| **per hour** | **~10,300** |

An hour yields 3,600 CPU-seconds per vCPU:

| target utilisation | vCPU |
|---|---|
| 100% — where case 13 broke | 2.9 |
| **80% — case 12 ran healthy at 81%** | **3.6** |
| 50% — comfortable | 5.7 |

## The answer

**4 vCPU, and it is now a measurement rather than arithmetic.**

[The vertical-scale sweep](findings-vertical-scale.md) ran case 13 on 4 vCPU on 21 Oct: zero
failures against 467, p95 **434 ms against 56,714**, and **application CPU at 49–55% where 2 vCPU
sat pinned at 94–99%**. That gives a directly comparable anchor:

| | CPU s for the hour | app CPU at 4 vCPU |
|---|---|---|
| case 13, measured | ~8,300 | **49–55%** |
| **this scenario, estimated** | **~10,300** (1.24×) | **~61–68%** |

**So 4 vCPU holds it, with roughly a fifth of the box to spare.** That is a more useful answer than
the earlier "floor of 4, provision 8", and it rests on a run rather than on a ratio.

The cliff is still the reason not to run it close: [case 13 on 2 vCPU](findings-case13.md) lost 38%
of its throughput to 47% more load. 61–68% leaves room; 85% would not.

> **8 vCPU is no longer the obvious upgrade.** The sweep found **RDS moving 33% → 41%** once the
> application stopped throttling it, narrowing the gap between the tiers from about 65 points to
> about 13. More application CPU may simply hand the constraint to the database, which four
> earlier runs could never make bind. **If this scenario needs more than 4 vCPU, measure where the
> next constraint actually is before buying more of the last one.**

## What is not the app server's problem

**13 minutes of media transfer per sync.** 160 files × 4 s each, serial, before any data moves. A
sync becomes 15–20 minutes and **~375 devices are in flight** at any moment.

That sounds alarming and mostly is not, for the server: media is pushed **first and serially**, so
each device issues one `uploadUrl` every four seconds — a trickle, not a burst. At ~90 rps with
~50 ms requests that is single-digit requests in flight. **Device concurrency is 375; server
concurrency is not.**

What it is: **~120 GB to S3 in an hour** (1,500 × 160 × 500 KB), and a field worker waiting a
quarter of an hour for a sync. Those are the real constraints of this scenario and neither is
CPU — which is worth saying plainly, because the vCPU number above is the easy part to act on and
the least likely to be what hurts.

## What would make this estimate wrong

**`uploadUrl` CPU is inferred.** ~8 ms is the single largest lever here and the one input nobody
measured. **The fix is one extra run**: the scenario at the default media rate and again at 8 per
encounter, everything else identical, and `ΔCPU ÷ Δ(uploadUrl calls)` is the answer. Hold the
cohort, the dataset and `MEDIA_UPLOAD_KBPS` constant — changing the pause changes the arrival
shape as well as the volume. `tools/cpu-per-sync.py` gives the CPU side; the call counts come from
the New Relic backup.

**20 encounters a day is the customer's median**, so p95 syncs push more, and the ×8 media
multiplier compounds on exactly those. A distribution would raise the tail well above these
figures.

**It is `encounter`, not `program_encounter`.** That is what their current bundle exports; the
programme design is out of scope and the generated datasets carry no enrolments to hang program
encounters off. `StorageProfiles` puts `ProgramEncounter` at the **highest** measured rate of any
entity, so a programme-shaped future costs more than this.

~~**CPU must scale with vCPU**~~ — **settled, 21 Oct 2026**, and it does. See
[`findings-vertical-scale.md`](findings-vertical-scale.md): case 13, the only run that ever broke,
passes on 4 vCPU with **zero failures and p95 434 ms against 56,714**. That premise is no longer
load-bearing.

**Co-tenant cost is a difference of two runs**, cases 6 and 7, not a direct measurement, and it
assumes their mix at 792/h resembles that run's.

## Scoring it afterwards

When this runs, four numbers decide whether the model held:

1. **requests per sync** — predicted ~215
2. **CPU seconds per customer sync** — predicted ~5.96, from `cpuPerCustomerSync`
3. **total CPU seconds for the hour** — predicted ~10,300
4. **where application CPU sat** — predicted 61–68% on 4 vCPU — **and whether RDS moved**, since
   the sweep suggests the database is the next thing to bind

**Record all four against the predictions here**, including when they are wrong. The campaign has
already published one figure that did not survive its context — 12.85 Mrec/h read as a ceiling
when it was a saturated server's throughput — and an estimate nobody scores becomes folklore.
