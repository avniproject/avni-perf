# Sourced. The app hosts the environment has now, one per line of app_instance_count.
# resize-env.sh writes app-instances after every apply; without it, the one original host.
APP_IDS_FILE=/Users/joy/avni-campaign/app-instances
APP_FIRST=i-044c88e15e8ea9e0f
app_ids(){ if [ -s "$APP_IDS_FILE" ]; then tr ',' ' ' < "$APP_IDS_FILE"; else echo "$APP_FIRST"; fi; }
app_ids_csv(){ app_ids | tr ' ' ',' | sed 's/,$//'; }
sshto(){ local id=$1; shift; ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=30 -o ProxyCommand="$PROXY %h" ubuntu@$id "$@" 2>/dev/null; }
# One read with three tries: EICE refuses ssh under a burst.
sshto_retry(){ local out i; for i in 1 2 3; do out=$(sshto "$@") && [ -n "$out" ] && { echo "$out"; return 0; }; sleep 10; done; echo "$out"; return 1; }
ping_of(){ sshto "$1" 'curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8021/ping'; }
