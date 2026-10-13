# Stopping and resuming co-tenant provisioning

`provision-co-tenants.sh` is resumable across an environment stop/start. This records
what that rests on, the one hazard, and the procedure.

## Why resume works

Three things were checked on 12 Oct 2026 mid-run, not assumed:

1. **State is server-side.** The resume guard is `GET /organisation`, re-read before every
   tenant, and it skips any name already present. The organisations live in RDS, so they
   survive an EC2 stop entirely. Losing the TSV log would not break resume.
2. **The working directory is on persistent storage.** `/home/ubuntu/cotenants` is on
   `/dev/root` — `nvme0n1p1`, the 60 GB root EBS volume, 17% used. Root EBS survives
   stop/start; only instance store and `/tmp` are cleared. Bundles, recipe and
   `provisioning.tsv` are all there.
3. **Re-scanning the done tenants is cheap.** At 162 organisations the guard response was
   37,791 bytes in 0.019 s. Extrapolated to 513 that is ~120 KB per call, so walking past
   all 513 tenants to reach the resume point costs well under a minute. `--from` exists but
   is not needed for speed — and should be avoided, because it would also skip retrying any
   tenant that had FAILED.

What does *not* survive is the loop process itself. `setsid nohup` survives an SSH
disconnect, not an instance stop. Relaunch is manual.

## The one hazard: the organisation in flight at kill time

`provision-org.sh` creates the organisation first and imports the bundle second. The guard
matches on **name presence only**. So an organisation killed mid-import is present by name,
incomplete in content, and will be *skipped* on resume — a silent hole in the dataset.

**Detection is exact.** A TSV row is written only after `provision-org.sh` returns, so:

    co-* on the server  −  names in provisioning.tsv  =  {pre-existing skips} ∪ {in flight}

Verified live: server had 145, TSV had 142, and the difference was exactly `co-001`,
`co-002` (the two pre-existing skips, logged as such) and `co-145` (then in flight).

Record the pre-existing skips so the morning check has a known-good baseline:
**co-001 and co-002**.

## Stopping

**With the updated script** (12 Oct 2026) the loop stops on a tenant boundary by itself:

    kill -TERM $(cat ~/cotenants/provisioning.tsv.pid)

It finishes the import in hand, prints `stopped after co-NNN, between tenants`, and exits 0.
Send the signal to that pid specifically. Do **not** use `pkill -f` — it also matches the
forked subshell running the current import, and would kill the import itself, which is the
very thing the signal exists to avoid.

**With the copy still deployed on the server tonight** (the pre-change version, which has no
trap), stop on a row boundary by hand instead:

    tail -n 0 -f ~/cotenants/provisioning.tsv | while read -r l; do
      pkill -f "[p]rovision-co-tenants.sh"; echo "stopped cleanly after: $l"; break
    done

The bracket form `[p]rovision` matters: a bare pattern matches the killing shell itself.
If this races and does kill an import mid-flight, the updated script catches it next morning
on the completeness check — see below.

Then, from the laptop, in this order — EC2 before RDS:

    aws ec2 stop-instances --instance-ids i-044c88e15e8ea9e0f i-041afc7c6e0761195
    aws rds stop-db-instance --db-instance-identifier avni-loadtest

## Starting

RDS first, and **wait for `available`** before anything else:

    aws rds start-db-instance --db-instance-identifier avni-loadtest
    aws rds describe-db-instances --db-instance-identifier avni-loadtest \
      --query 'DBInstances[0].DBInstanceStatus' --output text
    aws ec2 start-instances --instance-ids i-044c88e15e8ea9e0f

Do not gate on `/ping`. It answers 200 while RDS is still `starting` — proven, and the
reason `env-teardown.sh start` warms up too early.

The updated script runs the orphan check itself, on every tenant it is about to skip: it
compares the organisation's concept count to the bundle's and refuses to continue (exit 5,
naming the organisation and both counts) if it is short. An interrupted pass also leaves
`provisioning.tsv.inflight`, and the next run refuses to start (exit 4) until it is dealt
with. Neither depends on the other, which is deliberate — the marker catches a kill the
completeness check could miss (a bundle with no concepts), and the check catches an
interruption that left no marker, which is exactly the case if the stop happened under the
old script.

To check by hand anyway, on the app host:

    curl -s --max-time 60 "http://localhost:8021/organisation?size=5000" \
      -H "Accept: application/json" -H "USER-NAME: admin" \
    | grep -o '"name"[[:space:]]*:[[:space:]]*"co-[0-9]*"' \
    | sed 's/.*"\(co-[0-9]*\)"/\1/' | sort > /tmp/srv.txt
    awk -F'\t' 'NR>1{print $1}' ~/cotenants/provisioning.tsv | sort > /tmp/log.txt
    comm -23 /tmp/srv.txt /tmp/log.txt

Expect exactly `co-001` and `co-002`.

**Removal is still an unsettled loose end.** If an organisation does come back short, the
script now stops and names it — but it cannot clean it up. `teardown_org.py --scope all`
empties every org-scoped table including metadata, yet does not drop the `organisation` row
or its `db_user`, and the guard keys on the name, so an emptied-but-present organisation is
still skipped. The removal SQL is worth settling before it is needed rather than at 2 a.m.

## Import time drifts up with server uptime

Push-dominated imports rose from ~72 s to ~80 s over ~380 imports and ~12 h of uptime, and a
restart put them back to ~69 s with more organisations present than before — so it tracks
uptime, not tenant count, and is not worth planning around. Mechanism unestablished.

## Tests

`tools/tests/test-provision-co-tenants.sh` — 29 cases in about 10 s against a stub server
and a stub `provision-org.sh`: no AWS, no avni-server, no database. It covers the happy
path, skipping what is complete, refusing to skip what is short, the in-flight marker on a
hard kill, SIGTERM finishing the tenant in hand, resume after a clean stop, the original
blind-guard and truncated-list aborts, and a failed import being logged without ending the
run. Seven mutations of the guards were each confirmed to turn it red.

Relaunch, unchanged, from `~/cotenants`:

    cd ~/cotenants && setsid nohup ./tools/provision-co-tenants.sh \
      --url http://localhost:8021 --recipe datasets/co-tenants-day-180.json \
      --bundle-root /home/ubuntu/cotenants/bundles \
      --log /home/ubuntu/cotenants/provisioning.tsv \
      > /home/ubuntu/cotenants/provision.log 2>&1 &

`--url http://localhost:8021` is deliberate: the app host cannot reach its own ALB, whose
security group admits only the injector CIDR.

Note the log's `[HH:MM:SS]` stamps are host-local, which is **UTC** — 5h30 behind IST. The
TSV's `at` column is explicit `...Z`. A stalled-looking log is usually just that offset.
