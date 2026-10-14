# Case 7: their activity costs 18% per record; their presence cost 0.3%

**14 October 2026.** `2026-10-14T09-19-33Z-case7-33396d9`. Case 6's run with `CO_TENANTS=on` at
792 syncs/hour — Q4's busiest recorded hour across all of production. 280 customer syncs and
1,584 co-tenant syncs, 61,683 requests, **zero failures**, 2 h 00 m 50 s.

Cases 5, 6 and 7 are the same customer workload three times over, on identical settings and a
residue-free dataset. They separate infrastructure sharing into its two parts.

## The three-way comparison, customer syncs only

The aggregate Gatling summary is misleading here — it mixes 1,584 small co-tenant syncs into the
same numbers and reports a *lower* mean than case 6. Only the customer population compares.

| incremental customer syncs | case 5 | case 6 | case 7 | 5 → 7 |
|---|---|---|---|---|
| syncs | 280 | 280 | 280 | — |
| full syncs | 2 | 2 | 2 | — |
| records per sync, mean | 12,870 | 12,898 | 12,891 | +0.2% |
| duration p50 | 60.6 s | 60.6 s | 61.2 s | +0.9% |
| duration p95 | 182.2 s | 182.3 s | 184.4 s | +1.2% |
| server ms p50 | 3,577 | 3,560 | 4,163 | +16.4% |
| server ms p95 | 11,004 | 11,181 | 13,425 | +22.0% |
| **server ms per record** | **0.336** | **0.337** | **0.398** | **+18.2%** |

**Presence is free and activity is not.** 5 → 6 moved the per-record cost by 0.3%; 6 → 7 moved it
by 18.1%. The question cases 6 and 7 exist to separate has a clean answer: what costs the customer
is other tenants *working*, not other tenants *existing*.

## The device barely notices, and that is not a contradiction

Sync wall-clock rose 0.9% at p50 while server time rose 16.4%. Both are true because **server time
is about 7% of a sync**: the p50 sync takes 61.2 s and spends 4.2 s of it waiting on the server.
The rest is the client model's own processing. An 18% rise in a 7% component is a 1.2% rise
overall, which is what the duration columns show.

So the honest statement of impact depends on who is asking. **The server works 18% harder per
record. The device finishes about one percent later.**

## It is CPU on both tiers, and it is not the predicted mechanism

`CoTenantLoad` predicts that spreading load across 513 tenants "touches five times the pages for
the same request rate" and lands on the customer as a buffer cache hit rate. The measurements do
not support that:

| | case 6 | case 7 |
|---|---|---|
| RDS CPU | 4.7% | **21.1%** |
| app CPU | 7.6% | **27.1%** |
| ReadIOPS | 11.5 | 24.9 |
| **ReadLatency** | **0.0 ms** | **0.0 ms** |
| DatabaseConnections | 10 | 10 |

**Read latency did not move and neither did the connection count.** Records served rose 2.57x
(3.6 M to 9.3 M) while ReadIOPS rose only 2.2x and latency stayed sub-millisecond throughout — the
working set is still cached, so pages are not being evicted and re-read. Whatever the extra 18%
is, it is not disk.

It is CPU, on both tiers, and **nothing is close to saturated**: 27% app, 21% RDS, and the
connection pool flat at 10 of 10 across both runs. That rules out queueing as well. The cost is
*work per record*, not contention for a scarce resource — which is the more interesting answer,
because headroom will not make it go away.

**A mechanism worth testing, not a conclusion.** The ten connections now serve 523 organisations
rather than ten, and per-connection catalog and statement caches grow with the distinct schemas a
backend touches. That is the same structure that made a teardown scan 4.4 GB per user the day
before. It would produce exactly this signature — CPU up, IO flat, nothing saturated — but nothing
here establishes it. A run with the co-tenant load concentrated in ten organisations instead of
513, at the same aggregate rate, would separate "many tenants" from "more load".

## The co-tenants' own syncs cost far more per record

| | records/sync | server ms per record |
|---|---|---|
| customer | 12,891 | 0.398 |
| co-tenant | 3,584 | **0.961** |

2.4x the per-record cost for syncs a quarter the size, which is per-sync fixed cost amortised over
fewer records rather than anything about the tenants. Worth remembering when sizing: 1,584
co-tenant syncs produced 5.68 M records, **61% of everything the server returned in this run**.

## Provenance

Case 7's harness is `33396d9`, case 6's `cf77819`. The only code difference is the block that turns
an unusable co-tenant feeder from a warning into an exception, and it executes solely under
`CO_TENANTS=on` — dead code during case 6. Everything else came from case 5's own
`run-metadata.json`.

The first launch was mis-specified and discarded: `CO_TENANT_SECONDS` defaulted to `rampPeriod`
(33,640 s, the arrival window) rather than the run, so the customer finished at two hours while the
co-tenant stream was 22% through a nine-hour injection. The rate was correct throughout — the
default is fixed in `7f31f69`.
