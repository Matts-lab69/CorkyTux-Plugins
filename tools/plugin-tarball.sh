#!/usr/bin/env bash
set -euo pipefail

# Build the release tarball of one plugin, plus checksums.txt.
#
#   tools/plugin-tarball.sh <plugin-id> [output-dir]
#
# The tarball is <id>-<version>.tar.gz and holds a single top-level
# <id>/ directory, which is what the launcher expects: it extracts the
# archive inside ~/.local/share/CorkyTux/plugins and then looks for
# <id>/plugin.json in the new directory.
#
# The script does not publish anything. It prints the gh command to run
# once the tarball is reviewed.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ $# -lt 1 || $# -gt 2 ]]; then
  echo "Usage: tools/plugin-tarball.sh <plugin-id> [output-dir]" >&2
  exit 2
fi

ID="$1"
OUTDIR="${2:-$ROOT/dist}"

[[ -d "$ID" ]] || { echo "No such plugin directory: $ID" >&2; exit 2; }
[[ -f "$ID/plugin.json" ]] || { echo "$ID/plugin.json is missing" >&2; exit 2; }

mapfile -t META < <(python3 - "$ID/plugin.json" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
for key in ("id", "version", "entry"):
    value = data.get(key)
    if not isinstance(value, str) or not value:
        sys.exit("plugin.json is missing a valid %r" % key)
    print(value)
PY
)
JSON_ID="${META[0]}"
VERSION="${META[1]}"
ENTRY="${META[2]}"

[[ "$JSON_ID" == "$ID" ]] || {
  echo "plugin.json id '$JSON_ID' does not match the directory '$ID'" >&2
  exit 1
}
[[ -f "$ID/$ENTRY" ]] || { echo "Entry not found: $ID/$ENTRY" >&2; exit 1; }
[[ -x "$ID/$ENTRY" ]] || { echo "Entry is not executable: $ID/$ENTRY" >&2; exit 1; }

mkdir -p "$OUTDIR"
OUTDIR="$(cd "$OUTDIR" && pwd)"
TARBALL="$OUTDIR/$ID-$VERSION.tar.gz"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# Copy the plugin as-is minus the development files. tests/, caches and
# backups never travel: the registry tarball is the runtime payload.
mkdir -p "$STAGE/$ID"
tar -C "$ID" \
  --exclude='./tests' \
  --exclude='./tests/*' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.pytest_cache' \
  --exclude='*.bak' \
  --exclude='*.bak-*' \
  --exclude='.git' \
  -cf - . | tar -C "$STAGE/$ID" -xf -

# Top-level <id>/ only: the launcher extracts in the plugins directory and
# looks for the new directory that holds plugin.json.
tar --owner=0 --group=0 -czf "$TARBALL" -C "$STAGE" "$ID"

( cd "$OUTDIR" && sha256sum "$ID-$VERSION.tar.gz" > checksums.txt )

echo "Built: $TARBALL"
echo ""
echo "Contents:"
tar tzf "$TARBALL"
echo ""
echo "Checksums:"
cat "$OUTDIR/checksums.txt"
echo ""
echo "Publish (not run by this script):"
echo "  gh release create $ID-v$VERSION \\"
echo "    $TARBALL $OUTDIR/checksums.txt \\"
echo "    --title \"<title>\" --notes \"<notes>\""
