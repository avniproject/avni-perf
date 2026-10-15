# Case 12: compression costs 170% per record, and the run exceeded the recorded ceiling

**15 October 2026.** `2026-10-15T04-01-52Z-case12-c2a0e76`. Case 6 compressed into one hour —
`SYNC_WINDOW_HOURS=1`, 1,682 syncs/hour, **6.59 in flight against case 6's 0.55**. Co-tenants
present and syncing nothing, exactly as in case 6. 1,682 syncs, 31,409 requests, **zero failures**,
1 h 01 m 43 s.

## The same work, twelve times denser

| incremental customer syncs | case 6 | case 12 | delta |
|---|---|---|---|
| syncs | 280 | 1,682 | — |
| records per sync, mean | 12,898 | 12,805 | −0.7% |
| duration p50 | 60.6 s | 65.5 s | +8.0% |
| duration p95 | 182.3 s | 201.7 s | +10.6% |
| server ms p50 | 3,560 | 8,673 | +143.6% |
| server ms p95 | 11,181 | 30,950 | +176.8% |
| **server ms per record** | **0.337** | **0.911** | **+170.1%** |

Records per sync is unchanged to within a percent, so this is the same unit of work asked for
twelve times as often. **It costs 2.7x as much server time per record.** That is not more work; it
is the same work made more expensive by being concurrent, which is the definition of contention.

**The device still barely notices** — p50 sync duration up 8%. Server time remains a minority of a
sync even at 8.7 s, because the client model's own processing dominates. The gap between "+170% on
the server" and "+8% on the device" is the same arithmetic as case 7, an order of magnitude larger.

## Where it went, and it is the app server

| | case 6 | case 12 |
|---|---|---|
| **app CPU** | 7.6% | **81.0%, peak 92.5%** |
| RDS CPU | 4.7% | 23.8% |
| ReadIOPS | 11.5 | 125.2 |
| **ReadLatency** | **0.0 ms** | **0.0 ms** |
| DatabaseConnections | 10 | 15, peak 19 |

**The application server is the constraint and the database is not**, which is now the fourth
independent run to say so. ReadIOPS rose 10.9x and read latency did not move at all — the working
set is still served from cache. RDS sat at 23.8% while the app ran at 81% with peaks of 92.5%.

At 92.5% peak this run came close to the edge without going over: 1,682 of 1,682 syncs completed
and nothing failed. Case 13 adds 792 co-tenant syncs/hour on top of this, and on these numbers it
is the first run in the suite with a real chance of saturating.

## It delivered 21.0 Mrec/h, and the recorded ceiling is 12.85

This needs reconciling rather than celebrating.

| | records | wall | rate |
|---|---|---|---|
| case 6 | 3,617,090 | 7,248 s | 1.8 Mrec/h |
| **case 12** | **21,647,550** | **3,703 s** | **21.0 Mrec/h** |
| case 9/12b, recorded ceiling | — | — | 12.85 Mrec/h without push |

`findings-case9-12b.md` put the ceiling at **12.85 Mrec/h without push**, holding "across 2 sync
modes and 18–435 devices in flight". Case 12 sustained **21.0 Mrec/h for an hour with no failures
and 19 percentage points of app CPU still unused**. Both cannot be a property of the same system.

Three candidates, none established here:

* **The indexes are new.** This dataset was reloaded on 14 Oct and the reset included a `REINDEX`
  of all ten transactional tables — the first time this suite has measured on freshly built
  B-trees. The execution plan already flags index state as a parity caveat: "post-load indexes are
  pristine; production's carry accumulated bloat."
* **The ceiling was measured on a ramp, not a steady state.** 12a and 12b were stress profiles
  pushed until they broke; the figure is where failures began, not the last rate sustained
  cleanly. A ramp that breaks at X does not prove X cannot be held.
* **Record accounting may differ by sync mode.** 12b ran `SYNC_MODE=full`; this is `realistic`.

**Resolved by case 13 the same day: 12.85 is the throughput of a *saturated* server, not a
ceiling.** Case 13 saturated at 95.5% app CPU and settled at 13.0 Mrec/h — within 1.2% of 12b's
figure — while case 12 below the knee delivered 21.0. See [`findings-case13.md`](findings-case13.md).
The original reasoning is kept below because the three candidates it lists remain partly live:
fresh B-trees may still account for some of case 12's 21.0.

The cheapest discriminator is a `realistic` steady run at a rate between the two — if 21 Mrec/h
holds and 12.85 was a ramp artefact, the ceiling number in `findings-case9-12b.md` needs
qualifying, and every capacity statement derived from it with it.

## Provenance

Harness `c2a0e76`, deployed for this run; case 6 ran `cf77819`. The only `src/gatling` difference
is `7f31f69`'s `CO_TENANT_SECONDS` default, which executes solely under `CO_TENANTS=on` and is
therefore dead code in both case 6 and case 12. Case 13 will run on the same `c2a0e76`, so the
12 → 13 pair differs in one property.

Push is **off**, matching case 6. Case 11 — the other clustered run — used `push=on`, so case 12
is case 6 compressed rather than case 11 with co-tenants present.
