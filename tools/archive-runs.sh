#!/usr/bin/env bash
# Give every run under artefacts/ a one-file archive, where it has none.
#
# WHY
#   A Gatling report is ~250 objects that only work together: index.html pulls
#   js/, style/ and four SVGs by relative path, so a presigned URL for any one
#   object renders an unstyled page with no charts, and the bucket is private
#   with no website endpoint, so the directory cannot be browsed either. One zip
#   downloads in a click from the console, unzips to a folder named for the run
#   and opens offline with every drill-down page intact. It is nearly free: the
#   report is text, and a 130 MB run compressed to 6.8 MB in 3.5 s.
#
#   Runs made after 21 Oct 2026 get their archive from the injector's run script.
#   This back-fills the ones from before, and any run whose injector did not
#   zip -- the media-hour run of 21 Oct 2026 ran under the old script.
#
# Safe to re-run: a run that already has <run-id>.zip is skipped. The archive is
# built from the parent directory with the run id as the argument, so it carries
# one top-level folder rather than scattering 250 files into Downloads.
#
#   ./tools/archive-runs.sh [--bucket avni-loadtest-<account>] [--prefix artefacts]
#                           [--only <run-id>] [--dry-run]
set -euo pipefail

BUCKET=""; PREFIX="artefacts"; ONLY=""; DRY=0
while [ $# -gt 0 ]; do
  case "$1" in
    --bucket)  BUCKET="$2"; shift 2 ;;
    --prefix)  PREFIX="$2"; shift 2 ;;
    --only)    ONLY="$2";   shift 2 ;;
    --dry-run) DRY=1;       shift ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$BUCKET" ]; then
  ACCT=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || {
    echo "No AWS credentials, and no --bucket given." >&2; exit 1; }
  BUCKET="avni-loadtest-${ACCT}"
fi
command -v zip >/dev/null || { echo "zip is not installed" >&2; exit 1; }

WORK=$(mktemp -d "${TMPDIR:-/tmp}/archive-runs.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

RUNS=$(aws s3api list-objects-v2 --bucket "$BUCKET" --prefix "${PREFIX}/" --delimiter / \
         --query 'CommonPrefixes[].Prefix' --output text | tr '\t' '\n' \
       | sed "s|^${PREFIX}/||; s|/$||" | sort)
[ -n "$RUNS" ] || { echo "no runs under s3://$BUCKET/$PREFIX/" >&2; exit 1; }

made=0; skipped=0
for r in $RUNS; do
  [ -z "$ONLY" ] || [ "$r" = "$ONLY" ] || continue
  key="$PREFIX/$r/$r.zip"
  if aws s3api head-object --bucket "$BUCKET" --key "$key" >/dev/null 2>&1; then
    skipped=$((skipped+1)); continue
  fi
  if [ "$DRY" = 1 ]; then echo "would archive  $r"; continue; fi

  printf '%s' "$r"
  aws s3 sync --only-show-errors "s3://$BUCKET/$PREFIX/$r/" "$WORK/$r/"
  # -X: no uid/gid extra fields; the archive should look the same from any host.
  ( cd "$WORK" && zip -q -r -9 -X "$r.zip" "$r" )
  aws s3 cp --only-show-errors "$WORK/$r.zip" "s3://$BUCKET/$key"
  printf '  %s <- %s\n' "$(du -h "$WORK/$r.zip" | cut -f1)" "$(du -sh "$WORK/$r" | cut -f1)"
  rm -rf "$WORK/$r" "$WORK/$r.zip"
  made=$((made+1))
done
echo "archived $made, skipped $skipped already archived"
