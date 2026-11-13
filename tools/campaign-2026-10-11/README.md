# Load-test campaign scripts, 27 Oct – 6 Nov 2026 (execution-plan rows 27–37)

**A record of how the runs were driven, not a supported tool.** These are the shell chains that ran
rows 27–36 unattended — reset, resize, reload, warm-up, run, write-up, capture, stop — copied here on
9 Nov 2026 so the method behind every number in [`execution-plan.md`](../../docs/execution-plan.md)
and [`findings-summary.md`](../../docs/findings-summary.md) survives the laptop they ran on. They ran from
`~/avni-campaign/` (not the scratchpad, which `/tmp` cleanup sweeps) and still carry its absolute paths
(`/Users/joy/...`, `~/avni-campaign/...`); to reuse one, change those first.

Local state they read and write lives beside them in `~/avni-campaign/` and is **not** copied here:
`app-instances` (the app hosts' ids, written by `resize-env.sh`), `injector-class.override`, `jars/`
(the release-candidate jar, fetched from the deployables bucket), logs and phase timings.

## The pieces everything else uses

| file | what it does |
|---|---|
| `lib-chain.sh` | Sourced by chains from row 34 on. **From 14 Nov:** every connection re-reads credentials when they are within 5 minutes of lapsing, every wait loop checks the session, and each run's id is recorded at launch (`run_id_of`) for its write-up. Session handling that **waits** for an MFA refresh instead of aborting; `prepare_bed` (start without app hosts, resize database and injector, reload from the injector); `bring_up_apps` (resize or create copies, start them one at a time, jar, per-copy checks); `warm_up` with a relative spread check; `watch_run` with the 1%-for-two-ticks stop rule; `archive_logs` (only files new since the last archive); `launch_and_watch`; background write-ups. |
| `app-hosts.sh` | The app hosts the environment has now (`app_instance_count`, row 32), and ssh helpers with retries. |
| `resize-env.sh` | Resize app, database and injector **through tofu**, with an optional app count; refuses a plan that would replace any host or destroy an original; configures new copies; `keep` leaves the app class alone. |
| `deploy-jar.sh` | Put a jar on every app host, one at a time, with sha checks before and after. |
| `run-anchor.sh`, `run-anchor-30.sh`, `swap-jar.sh` | Anchor runs A–D for rows 27–30. |
| `generate-25k.sh` | Row 37's dataset: generate, split into feeders, stream to S3. |
| `db-small-and-stop.sh` | After the campaign (12 Nov): start the stopped database, resize it through tofu to `db.m6g.large` with every other variable at its current value (refusing any other change), and stop it — resetting AWS's 7-day auto-start so the next one comes up small. |

## The chains, by row

| row(s) | chain | capture and stop |
|---|---|---|
| 29, 29b | `chain-row29*.sh`, `chain-row29b*.sh` (plus `-resume` / `-1098` / `-1103` variants) | `capture-and-stop-4.sh` (after the #1100 chain, 28 Oct) |
| 30 | `chain-row30-AC.sh`, `chain-row30-AC-recover.sh`, `chain-row30-BD.sh` | `capture-and-stop-5.sh` (A/C), `-6.sh` (B/D) |
| 31 | `chain-row31-ramp.sh`, `chain-row31-ramp-resume.sh`, `chain-row31-steady.sh` | `capture-and-stop-7.sh` |
| 33 | `chain-row33.sh`, then `chain-row33-resume.sh` (the first aborted on a warm-up check whose floor a 100-device warm-up cannot reach) | `capture-and-stop-33.sh` |
| 34 (ramp) | `chain-row34-ramp.sh`, then `chain-row34-ramp-resume.sh` (the local jar had left `~/Downloads`) | — |
| 34 (steady pair), 35 | `chain-rows34-35.sh` — order chosen so row 35 finished the same day | in the chain |
| 36 (37 held) | `chain-rows36-37.sh` — third copy created alongside the first reload | in the chain |
| 29c, 30b, 39 (with the 18.1 control re-run) | `chain-rows-29c-30b-39.sh`; row 39's user is `row39-user.sql` (district 1 of `state-1`, generator-shaped uuids so a reload removes it), applied only when `row39-sql.approved` holds its sha256 | in the chain |
| 29c, 39 (13 Nov, as run) | `chain-rows-29c-30b-39-resume.sh` (row 39 with the feeder path fixed), `-deep.sh` (deep pages first: `row39-merge-types.sql` merges three of District 1's encounter types into one 123-page stream, gated on `row39-merge.approved`), `-resume3.sh` (after the 19:27 credential expiry hung the deep chain) | in the chain |
| 29c B, 30b (Monday 16 Nov) | `chain-monday-29cB-30b.sh` — stops the environment as soon as the last run's logs are archived; run ids recorded at launch, so write-ups do not need the injector | in the chain |

**Every `-resume` exists because its chain stopped part-way,** and the execution plan's provenance notes
say why. The chains were never edited while running: bash reads a script by offset, so a running file is
replaced only by a new one.
