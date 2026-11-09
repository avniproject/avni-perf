#!/usr/bin/env bash
# Put a jar on the app server: push it over the EICE tunnel (the host has no S3 role), sha-check
# it there, stop the service, keep the current jar beside it as <name>.bak, install, start, wait
# for /ping, sha-check again.   ./deploy-jar.sh <local jar path> <expected sha256>
set -uo pipefail
LOCAL="${1:?local jar}"; SHA="${2:?sha256}"; JAR=$(basename "$LOCAL")
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] jar: $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"
. /Users/joy/avni-campaign/app-hosts.sh
# **Every app host, one after another** (rows 32+): each start runs Flyway, and a second copy
# starting while the first migrates is what serial: 1 avoids in the playbook. Re-invokes
# itself per host with APP set.
if [ -z "${APP:-}" ]; then
  for id in $(app_ids); do APP=$id "$0" "$@" || exit 1; done
  exit 0
fi
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] jar[$APP]: $*"; }
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
[ "$(shasum -a 256 "$LOCAL" | cut -d' ' -f1)" = "$SHA" ] || { say "ABORT: $LOCAL is not sha $SHA"; exit 1; }
CUR=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1)
[ "$CUR" = "$SHA" ] && { say "$JAR already deployed; nothing to do"; exit 0; }
if [ "$(sshapp "test -f /opt/avni_server/$JAR.bak && sudo sha256sum /opt/avni_server/$JAR.bak" | cut -d' ' -f1)" = "$SHA" ]; then
  say "$JAR is already on the host as $JAR.bak; using it"; sshapp "sudo cat /opt/avni_server/$JAR.bak > /tmp/$JAR"
else
  say "pushing $JAR over the tunnel (${CUR:0:12} deployed now)"
  cat "$LOCAL" | sshapp "cat > /tmp/$JAR && sha256sum /tmp/$JAR" | cut -d' ' -f1 | grep -q "^$SHA$" || { say "ABORT: push failed or sha mismatch on the host"; exit 1; }
fi
say "stopping avni_server_appserver; installing $JAR; keeping the current jar as a .bak"
sshapp "sudo systemctl stop avni_server_appserver && CURN=\$(for f in /opt/avni_server/*.bak; do [ \"\$(sudo sha256sum \$f | cut -d' ' -f1)\" = \"$CUR\" ] && echo have; done); [ -n \"\$CURN\" ] || sudo cp /opt/avni_server/avni-server.jar /opt/avni_server/previous-$CUR.jar.bak; sudo install -o \$(stat -c %U /opt/avni_server/avni-server.jar) -g \$(stat -c %G /opt/avni_server/avni-server.jar) -m 0755 /tmp/$JAR /opt/avni_server/avni-server.jar && sudo cp -n /tmp/$JAR /opt/avni_server/$JAR.bak; sudo systemctl start avni_server_appserver && sudo rm -f /tmp/$JAR && echo swapped" | grep -q swapped || { say "ABORT: swap failed on the host"; exit 1; }
for i in $(seq 1 30); do P=$(sshapp 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8021/ping'); [ "$P" = "200" ] && break; sleep 10; done
NEW=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1)
[ "$NEW" = "$SHA" ] && [ "$P" = "200" ] || { say "ABORT: after swap sha=${NEW:0:12} ping=$P"; exit 1; }
say "$JAR deployed and serving: sha ${NEW:0:12}, /ping 200"
