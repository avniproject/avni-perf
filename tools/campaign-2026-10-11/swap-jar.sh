#!/usr/bin/env bash
# Row 28: put the 17.3 jar (2c0215679) back from the .bak kept on the host at the 18.1 swap, or the
# 18.1 jar back from its .bak afterwards.   ./swap-jar.sh 17.3|18.1
set -uo pipefail
WANT="${1:?17.3 or 18.1}"
case "$WANT" in
  17.3) SRC=/opt/avni_server/avni-server-17.3-2c0215679.jar.bak; SHA=73d458d2a4a814e17225a9564cdc38ed9a7602c44b3e7c9c131962bf86ed471d; KEEP=/opt/avni_server/avni-server-18.1.0-789092feb.jar.bak;;
  18.1) SRC=/opt/avni_server/avni-server-18.1.0-789092feb.jar.bak; SHA=87bf747b08a9d2a90f5fa3e9a91cd137a295643976fb6491ae433d550e5ba678; KEEP=/opt/avni_server/avni-server-17.3-2c0215679.jar.bak;;
  *) echo "17.3 or 18.1" >&2; exit 2;;
esac
cd /Users/joy/projects/samanvay/avni/avni-infra
. provision/scripts/aws-session.sh avni-load-test </dev/null >/dev/null 2>&1; export AWS_REGION=ap-south-1
say(){ echo "[$(TZ=Asia/Kolkata date +%H:%M:%S)] jar: $*"; }
PROXY="$PWD/configure/scripts/eice-ssh-proxy.sh"; APP=i-044c88e15e8ea9e0f
sshapp(){ ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$APP "$@" 2>/dev/null; }
CUR=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1)
[ "$CUR" = "$SHA" ] && { say "$WANT already deployed; nothing to do"; exit 0; }
[ "$(sshapp "sudo sha256sum $SRC" | cut -d' ' -f1)" = "$SHA" ] || { say "ABORT: $SRC is missing or not the $WANT build"; exit 1; }
say "stopping avni_server_appserver; $WANT from $SRC; current kept as $KEEP"
sshapp "sudo systemctl stop avni_server_appserver && sudo cp -n /opt/avni_server/avni-server.jar $KEEP; sudo install -o \$(stat -c %U /opt/avni_server/avni-server.jar) -g \$(stat -c %G /opt/avni_server/avni-server.jar) -m 0755 $SRC /opt/avni_server/avni-server.jar && sudo systemctl start avni_server_appserver && echo swapped" | grep -q swapped || { say "ABORT: swap failed on the host"; exit 1; }
for i in $(seq 1 30); do C=$(sshapp 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8021/ping'); [ "$C" = "200" ] && break; sleep 10; done
NEW=$(sshapp 'sudo sha256sum /opt/avni_server/avni-server.jar' | cut -d' ' -f1)
[ "$NEW" = "$SHA" ] && [ "$C" = "200" ] || { say "ABORT: after swap sha=${NEW:0:12} ping=$C"; exit 1; }
say "$WANT deployed and serving: sha ${NEW:0:12}, /ping 200"
