#!/usr/bin/env bash
# EFM Go Prompt 01 verifier. Exit 0 only if source doors are closed and
# dist == backend static. Does NOT claim Windows runtime egress PASS.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FAIL=0
ok() { printf 'PASS  %s\n' "$*"; }
bad() { printf 'FAIL  %s\n' "$*"; FAIL=1; }

# 1. DOWNLOAD_BASE stays empty
if grep -n 'const DOWNLOAD_BASE = "https://' \
     "$ROOT/website/electron/auto-update.js" >/dev/null; then
  bad "DOWNLOAD_BASE must stay empty"
else
  ok "DOWNLOAD_BASE is empty"
fi

# 2. Mute stays on
if grep -n 'const EFM_MUTE_KIRO_UPDATES = true' \
     "$ROOT/website/electron/auto-update.js" >/dev/null; then
  ok "EFM_MUTE_KIRO_UPDATES=true"
else
  bad "EFM_MUTE_KIRO_UPDATES is not true"
fi

# 3. The auto-update test must not pin a foreign feed as DEFAULT_FEED_BASE
OLD_FEED="$(printf '%s%s' 'https://updates.crew.' 'kiro.dev/feed')"
if grep -n "DEFAULT_FEED_BASE, \"${OLD_FEED}\"" \
     "$ROOT/website/electron/test/auto-update.test.js" >/dev/null; then
  bad "auto-update.test.js still pins a foreign DEFAULT_FEED_BASE"
else
  ok "DEFAULT_FEED_BASE test is not pinned to a foreign feed"
fi

# 4. Catalog fetch disabled
if grep -n 'EFM_DISABLE_REMOTE_CATALOG = True' \
     "$ROOT/src/efm_go/apps/official_catalog.py" >/dev/null; then
  ok "EFM_DISABLE_REMOTE_CATALOG=True"
else
  bad "official_catalog.py missing EFM_DISABLE_REMOTE_CATALOG"
fi

# 5. Beacon default off + empty endpoint
if grep -n '_DEFAULT_BEACON_ENDPOINT = ""' \
     "$ROOT/src/efm_go/config/sections.py" >/dev/null \
   && grep -A2 'beacon_enabled: bool = field(' \
        "$ROOT/src/efm_go/config/sections.py" | grep -q 'default=False'; then
  ok "beacon default OFF and empty endpoint"
else
  bad "beacon still default ON or CloudFront endpoint remains"
fi

# 6. dist exists and matches backend static
DIST="$ROOT/website/dist"
STATIC="$ROOT/website/electron/backend-dist/efm-go-backend/Lib/site-packages/efm_go/static/dist"
hash_tree() {
  (cd "$1" && find . -type f ! -name 'build-info.json' -print0 | sort -z | xargs -0 sha256sum | sha256sum | awk '{print $1}')
}
if [[ ! -f "$DIST/index.html" ]]; then
  bad "website/dist/index.html missing"
elif [[ ! -f "$STATIC/index.html" ]]; then
  bad "backend-dist static/index.html missing"
else
  H1="$(hash_tree "$DIST")"
  H2="$(hash_tree "$STATIC")"
  if [[ "$H1" = "$H2" ]]; then
    ok "dist hash == backend static hash ($H1)"
  else
    bad "dist ($H1) != static ($H2)"
  fi
fi

# 7. build-info present
if [[ -f "$ROOT/website/electron/build-info.json" ]]; then
  ok "build-info.json present"
  python3 - "$ROOT/website/electron/build-info.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
need=("app_version","source_sha","build_time","website_dist_sha256","backend_static_sha256")
miss=[k for k in need if not d.get(k)]
if miss:
    print("FAIL  build-info missing", ",".join(miss))
    raise SystemExit(1)
print("PASS  build-info fields", ",".join(need))
PY
else
  bad "website/electron/build-info.json missing"
fi

# 8. backend-dist python copies match source doors
B_CAT="$ROOT/website/electron/backend-dist/efm-go-backend/Lib/site-packages/efm_go/apps/official_catalog.py"
B_SEC="$ROOT/website/electron/backend-dist/efm-go-backend/Lib/site-packages/efm_go/config/sections.py"
if [[ -f "$B_CAT" ]] && grep -q 'EFM_DISABLE_REMOTE_CATALOG = True' "$B_CAT"; then
  ok "backend-dist catalog door closed"
else
  bad "backend-dist official_catalog.py still fetches or missing"
fi
if [[ -f "$B_SEC" ]] && grep -q '_DEFAULT_BEACON_ENDPOINT = ""' "$B_SEC"; then
  ok "backend-dist beacon endpoint empty"
else
  bad "backend-dist beacon endpoint still CloudFront or missing"
fi

# 9. auto-update.js no longer names the foreign byte host, even in a comment
OLD_BYTE="$(printf '%s%s' 'download.crew.' 'kiro.dev')"
if grep -q "$OLD_BYTE" "$ROOT/website/electron/auto-update.js"; then
  bad "auto-update.js still names the foreign byte host"
else
  ok "auto-update.js has no foreign byte host"
fi

echo
if [[ "$FAIL" -ne 0 ]]; then
  echo "P-01 VERIFIER: FAIL"
  exit 1
fi
echo "P-01 VERIFIER: SOURCE+BUNDLE STATIC CHECKS PASS"
echo "RUNTIME_EGRESS_TEST=NOT_TESTED (Windows launch required for Prompt 01 PASS)"
exit 0
