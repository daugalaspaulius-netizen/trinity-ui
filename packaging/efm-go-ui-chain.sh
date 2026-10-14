#!/usr/bin/env bash
# EFM Go Prompt 01 — canonical UI packaging chain.
# website/src -> website/dist -> backend-dist static -> (optional) Electron.
# FAIL if dist hash != backend static hash. Do not pack a stale window.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WEBSITE="$ROOT/website"
DIST="$WEBSITE/dist"
ELECTRON="$WEBSITE/electron"
BACKEND_STATIC="$ELECTRON/backend-dist/efm-go-backend/Lib/site-packages/efm_go/static/dist"
MANIFEST="$ELECTRON/build-info.json"
PACK="${EFM_PACK:-0}"

hash_tree() {
  local dir="$1"
  # Same algorithm for every box: sorted sha256 of path+file hashes.
  # Exclude build-info.json so writing the manifest does not change the digest.
  (cd "$dir" && find . -type f ! -name 'build-info.json' -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
}

log() { printf 'EFM-CHAIN: %s\n' "$*"; }

if [[ ! -d "$ELECTRON/backend-dist/efm-go-backend" ]]; then
  echo "FAIL: website/electron/backend-dist/efm-go-backend missing. Stage Windows backend first." >&2
  exit 2
fi

log "clean website/dist (keep node_modules)"
rm -rf "$DIST"

log "vite build"
cd "$WEBSITE"
if [[ ! -d node_modules ]]; then
  if [[ -f package-lock.json ]]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi
fi
npm run build

if [[ ! -f "$DIST/index.html" ]]; then
  echo "FAIL: website/dist/index.html missing after build" >&2
  exit 3
fi

DIST_HASH="$(hash_tree "$DIST")"
log "website/dist hash=$DIST_HASH"

log "copy official_catalog.py + sections.py into backend-dist"
SRC_APPS="$ROOT/src/efm_go/apps/official_catalog.py"
SRC_SEC="$ROOT/src/efm_go/config/sections.py"
DST_APPS="$ELECTRON/backend-dist/efm-go-backend/Lib/site-packages/efm_go/apps/official_catalog.py"
DST_SEC="$ELECTRON/backend-dist/efm-go-backend/Lib/site-packages/efm_go/config/sections.py"
cp -f "$SRC_APPS" "$DST_APPS"
cp -f "$SRC_SEC" "$DST_SEC"
rm -f "$ELECTRON/backend-dist/efm-go-backend/Lib/site-packages/efm_go/apps/__pycache__/official_catalog"*.pyc
rm -f "$ELECTRON/backend-dist/efm-go-backend/Lib/site-packages/efm_go/config/__pycache__/sections"*.pyc

log "sync dist -> backend-dist static"
rm -rf "$BACKEND_STATIC"
mkdir -p "$(dirname "$BACKEND_STATIC")"
cp -a "$DIST" "$BACKEND_STATIC"

STATIC_HASH="$(hash_tree "$BACKEND_STATIC")"
log "backend static hash=$STATIC_HASH"

if [[ "$DIST_HASH" != "$STATIC_HASH" ]]; then
  echo "FAIL: dist hash != backend static hash" >&2
  echo "  dist   $DIST_HASH" >&2
  echo "  static $STATIC_HASH" >&2
  exit 4
fi

SOURCE_SHA="$(git -C "$ROOT" rev-parse HEAD)"
BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
APP_VERSION="$(python3 -c 'import json; print(json.load(open("'"$ELECTRON/package.json"'")).get("version",""))')"

cat > "$MANIFEST" <<EOF
{
  "app": "EFM Go",
  "app_version": "$APP_VERSION",
  "source_sha": "$SOURCE_SHA",
  "build_time": "$BUILD_TIME",
  "website_dist_sha256": "$DIST_HASH",
  "backend_static_sha256": "$STATIC_HASH",
  "hash_alg": "sha256-sorted-files"
}
EOF
cp -f "$MANIFEST" "$DIST/build-info.json"
cp -f "$MANIFEST" "$BACKEND_STATIC/build-info.json"

log "SOURCE_SHA=$SOURCE_SHA DIST=$DIST_HASH STATIC=$STATIC_HASH"
log "BUNDLE hashes match. Electron input is fresh UI."

if [[ "$PACK" = "1" ]]; then
  log "electron-builder --win portable"
  cd "$ELECTRON"
  export CSC_IDENTITY_AUTO_DISCOVERY=false
  npm run dist:win:portable
fi

log "DONE"
