#!/usr/bin/env bash
# Build the Chrome Web Store upload from extension/.
#
# The store requires the *contents* of the extension folder at the zip root,
# not the folder itself, and rejects any archive containing macOS metadata.
#
#   ./pack-extension.sh
#
set -euo pipefail
cd "$(dirname "$0")"

VERSION=$(python3 -c 'import json;print(json.load(open("extension/manifest.json"))["version"])')
OUT="dist/newsnownext-extension-${VERSION}.zip"

mkdir -p dist
rm -f "$OUT"

( cd extension && zip -qr "../$OUT" . \
    -x '.*' -x '__MACOSX/*' -x '*/.DS_Store' -x '.DS_Store' )

echo "Built $OUT  ($(du -h "$OUT" | cut -f1))"
echo
unzip -l "$OUT"
echo
echo "Reminder: bump \"version\" in extension/manifest.json before every resubmission."
