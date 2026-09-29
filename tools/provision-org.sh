#!/usr/bin/env bash
#
# Create an organisation and install an implementation bundle into it, through the server's own
# APIs. Metadata — concepts, forms, subject types, encounter types — is the half the data
# generator deliberately does not produce (H1), and this is how it gets there.
#
#   ./provision-org.sh --url https://host --bundle ~/Downloads/Tanuh.zip --name tanuh-load
#
# Three steps, because the server needs them separate:
#
#   1. POST /organisation as a **superadmin**. This also creates the org's db_user and its
#      implementation schema.
#   2. Create a user in the new org, in a group carrying privileges. The importer refuses a
#      superadmin (`assertIsNotSuperAdmin`), so step 3 cannot run as whoever ran step 1.
#   3. POST /import/new with `type=metadataZip` as that user. It is asynchronous — the file goes
#      to S3 and a Spring Batch job picks it up — so this polls /import/status rather than
#      assuming.
#
# Under AVNI_IDP_TYPE=none authentication is the USER-NAME header, so there are no passwords
# here. Against a Cognito environment this script does not apply.

set -uo pipefail

URL=""; BUNDLE=""; NAME=""; ADMIN="admin"; CATEGORY="7"; STATUS="1"
while [ $# -gt 0 ]; do
  case "$1" in
    --url)    URL="$2"; shift 2 ;;
    --bundle) BUNDLE="$2"; shift 2 ;;
    --name)   NAME="$2"; shift 2 ;;
    --admin)  ADMIN="$2"; shift 2 ;;
    # Seeded in order by V1_339_3 and V1_339_4, and there is no endpoint to look them up by name.
    # Categories: 1 Production, 2 UAT, 3 Prototype, 4 Temporary, 5 Trial, 6 Training, 7 Dev.
    # Statuses: 1 Live, 2 Archived. Both are NOT NULL on `organisation`, so they cannot be
    # omitted — the first attempt at this failed on exactly that.
    --category) CATEGORY="$2"; shift 2 ;;
    --status)   STATUS="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$URL" ] && [ -n "$BUNDLE" ] && [ -n "$NAME" ] || {
  echo "usage: $0 --url <base-url> --bundle <bundle.zip> --name <org-name> [--admin <username>]" >&2
  exit 2; }
# A directory is accepted and zipped, because that is the shape an implementation config repo is
# checked out in, while the server validates the upload's content type as a zip. Entries go in at
# the root — the importer looks for `concepts.json` and friends there, not under a folder.
CLEANUP_ZIP=""
if [ -d "$BUNDLE" ]; then
  SRC="$BUNDLE"
  # A single dot in the filename. `mktemp foo.XXXXXX` plus `.zip` gives `bundle.a1b2c3.zip`, and
  # the server rejects that outright as a double extension — a uniquely unhelpful way to fail on
  # a file it would otherwise accept. The randomness goes in the directory name instead.
  ZIPDIR="$(mktemp -d "${TMPDIR:-/tmp}/bundle.XXXXXX")"
  BUNDLE="$ZIPDIR/bundle.zip"
  CLEANUP_ZIP="$ZIPDIR"
  ( cd "$SRC" && zip -qr "$BUNDLE" . ) || { echo "error: could not zip $SRC" >&2; exit 2; }
  echo "zipped $SRC -> $(basename "$BUNDLE")"
elif [ ! -f "$BUNDLE" ]; then
  echo "error: no such bundle: $BUNDLE" >&2; exit 2
fi
trap '[ -n "$CLEANUP_ZIP" ] && rm -rf "$CLEANUP_ZIP"' EXIT
case "$BUNDLE" in *.zip) ;; *) echo "error: the bundle must be a .zip or a directory to zip" >&2; exit 2 ;; esac

api() { curl -s -w '\n%{http_code}' --max-time 120 "$@"; }
body() { printf '%s' "$1" | sed '$d'; }
code() { printf '%s' "$1" | tail -1; }
die()  { echo "  FAILED: $*" >&2; exit 1; }

SLUG="$(printf '%s' "$NAME" | tr '[:upper:] ' '[:lower:]_' | tr -cd 'a-z0-9_')"

echo
echo "Provisioning '$NAME' on $URL"
echo

# ---- 1. the organisation --------------------------------------------------------------------
echo "1. creating the organisation, as $ADMIN"
R=$(api -X POST "$URL/organisation" \
      -H 'Content-Type: application/json' -H "USER-NAME: $ADMIN" \
      -d "{\"name\":\"$NAME\",\"dbUser\":\"${SLUG}\",\"schemaName\":\"${SLUG}\",
           \"usernameSuffix\":\"${SLUG}\",\"mediaDirectory\":\"${SLUG}\",
           \"categoryId\":${CATEGORY},\"statusId\":${STATUS}}")
C=$(code "$R")
if [ "$C" = "201" ] || [ "$C" = "200" ]; then
  ORG_ID=$(body "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  ORG_UUID=$(body "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('uuid',''))" 2>/dev/null)
  echo "   created, id ${ORG_ID:-unknown}, uuid ${ORG_UUID:-unknown}, db_user $SLUG"
elif printf '%s' "$(body "$R")" | grep -qi "already\|duplicate\|exists"; then
  echo "   already exists, looking up its uuid"
  L=$(api "$URL/organisation?size=200" -H "USER-NAME: $ADMIN")
  ORG_UUID=$(body "$L" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin)
    rows=d.get('content') if isinstance(d,dict) else d
    print(next((o['uuid'] for o in rows if o.get('name')=='$NAME'), ''))
except Exception: print('')" 2>/dev/null)
  [ -n "$ORG_UUID" ] || die "could not find an organisation named '$NAME' to continue with"
  echo "   uuid $ORG_UUID"
else
  die "POST /organisation returned $C: $(body "$R" | head -c 300)"
fi

# The db_user is created here, and a role without grants reads nothing while /ping stays green.
echo
echo "   If reads later fail with 'permission denied for table users', the db_user needs grants:"
echo "     select grant_all_on_all('$SLUG');   -- via provision/scripts/db-bootstrap.sh"

# ---- 2. a user that is not a superadmin -----------------------------------------------------
#
# `POST /import/new` calls `assertIsNotSuperAdmin`, so step 3 cannot run as whoever ran step 1.
# The new org needs its own user, and `ORGANISATION-UUID` is what lets a superadmin act inside
# it — without that header the user would be created in the admin's own organisation instead.
UPLOADER="bundleloader@${SLUG}"
# The username carries the organisation's suffix and is not an address; `email` is validated as
# one and rejects it. They are separate fields for a reason, and the first attempt conflated them.
EMAIL="${PROVISION_EMAIL:-loadtest+${SLUG}@avniproject.org}"
# Validated with libphonenumber, so it has to be a real shape: Indian mobiles are ten
# digits starting 6-9. A run of zeros parses as NationalNumber 0 and is rejected.
PHONE="${PROVISION_PHONE:-+919999999999}"
echo
echo "2. creating $UPLOADER inside the new organisation"
[ -n "${ORG_UUID:-}" ] || die "no organisation uuid to scope the user to"

R=$(api -X POST "$URL/user" \
      -H 'Content-Type: application/json' -H "USER-NAME: $ADMIN" \
      -H "ORGANISATION-UUID: $ORG_UUID" \
      -d "{\"username\":\"$UPLOADER\",\"name\":\"Bundle loader\",
           \"operatingIndividualScope\":\"None\",
           \"groupIds\":[],\"email\":\"$EMAIL\",\"phoneNumber\":\"$PHONE\"}")
C=$(code "$R")
if [ "$C" = "200" ] || [ "$C" = "201" ]; then
  NEW_USER_ID=$(body "$R" | python3 -c "import json,sys; print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  echo "   created, id ${NEW_USER_ID:-unknown}"
elif printf '%s' "$(body "$R")" | grep -qi "already exists"; then
  echo "   already exists, looking up its id"
  # /user returns HAL (_embedded.user); /user/search/find returns content and takes a filter.
  U=$(api "$URL/user/search/find?username=$UPLOADER" -H "USER-NAME: $ADMIN" -H "ORGANISATION-UUID: $ORG_UUID")
  NEW_USER_ID=$(body "$U" | python3 -c "
import json,sys
try:
    d=json.load(sys.stdin); rows=d.get('content') if isinstance(d,dict) else d
    print(next((u['id'] for u in rows if u.get('username')=='$UPLOADER'), ''))
except Exception: print('')" 2>/dev/null)
  [ -n "$NEW_USER_ID" ] || die "could not find $UPLOADER to continue with"
else
  die "POST /user returned $C: $(body "$R" | head -c 300)"
fi

# Administrators carries the privileges the importer checks. Without a group the user resolves
# none, and the upload is refused on UploadMetadataAndData — which is the same shape as the G5
# defect on the generated users, arrived at from the other direction.
#
# Group ids are per organisation and there is no admin endpoint listing them, so this reads the
# sync endpoint the client uses. `hasAllPrivileges` is the thing to match on, not the name.
echo "   finding a group with all privileges"
G=$(api "$URL/groups/search/lastModified?lastModifiedDateTime=1900-01-01T00:00:00.000Z&now=2099-01-01T00:00:00.000Z&size=50&page=0" \
      -H "USER-NAME: $ADMIN" -H "ORGANISATION-UUID: $ORG_UUID")
GROUP_ID=$(body "$G" | python3 -c "
import json,sys
try:
    gs=json.load(sys.stdin).get('_embedded',{}).get('groups',[])
    print(next((g['id'] for g in gs if g.get('hasAllPrivileges')), ''))
except Exception: print('')" 2>/dev/null)
[ -n "$GROUP_ID" ] || die "no group with hasAllPrivileges in '$NAME' — organisation setup did not seed one"
echo "   group $GROUP_ID"

echo "   adding $UPLOADER to it"
R=$(api -X POST "$URL/userGroup" \
      -H 'Content-Type: application/json' -H "USER-NAME: $ADMIN" \
      -H "ORGANISATION-UUID: $ORG_UUID" \
      -d "[{\"userId\":${NEW_USER_ID:-0},\"groupId\":$GROUP_ID}]")
C=$(code "$R")
[ "$C" = "200" ] || [ "$C" = "201" ] || die "POST /userGroup returned $C: $(body "$R" | head -c 250)"
echo "   added"

# ---- 3. the bundle --------------------------------------------------------------------------
echo
echo "3. uploading $(basename "$BUNDLE") as metadataZip"
R=$(api -X POST "$URL/import/new" -H "USER-NAME: $UPLOADER" \
      -H "ORGANISATION-UUID: $ORG_UUID" \
      -F "file=@$BUNDLE;type=application/zip" \
      -F "type=metadataZip" -F "autoApprove=false" \
      -F "locationUploadMode=CREATE" -F "locationHierarchy=" -F "encounterUploadMode=")
C=$(code "$R")
[ "$C" = "200" ] || die "POST /import/new returned $C: $(body "$R" | head -c 400)"
echo "   accepted; the server runs it as a batch job"

# ---- 4. wait for it -------------------------------------------------------------------------
echo
echo "4. waiting for the job"
for _ in $(seq 1 60); do
  sleep 5
  S=$(api "$URL/import/status?size=1" -H "USER-NAME: $UPLOADER")
  [ "$(code "$S")" = "200" ] || continue
  STATUS=$(body "$S" | python3 -c "
import json,sys
try:
    c=json.load(sys.stdin).get('content') or []
    print(c[0].get('status','') if c else '')
except Exception: print('')" 2>/dev/null)
  case "$STATUS" in
    COMPLETED) echo "   COMPLETED"; break ;;
    FAILED)    die "the import job FAILED — check /import/errorfile" ;;
    "")        ;;
    *)         printf '   %s\r' "$STATUS" ;;
  esac
done

echo
echo "Done. Re-dump the metadata ids the generator needs:"
echo "  psql \"\$DB\" -At -f tools/data-generator/refs.sql > tools/data-generator/refs.json"
echo "Then it should report subject types and encounter types for the new organisation."
