#!/usr/bin/env bash
# Stage a Windows python-build-standalone backend under
# website/electron/backend-dist/efm-go-backend/ from a Linux host.
#
# Native Windows builds should keep using packaging/build-desktop.sh — that
# path executes python.exe natively. This script exists because EFM Go's
# Contabo packer is Linux: the previous WP3.4 portable exe shipped
# extraResources/backend-dist with only README.txt, so the packaged app
# refused to spawn (no PATH fallback).
#
# Wine 9.0 cannot run Windows pip/setuptools (KERNEL32.CopyFile2 unimplemented
# in python.exe metadata copy). Instead:
#   1. Copy a Windows PBS interpreter (uv)
#   2. Build a py3-none-any kirocrew wheel on Linux
#   3. pip-install Windows wheels into Lib/site-packages (--platform win_amd64)
#   4. Write the relocatable bin/kirocrew.cmd launcher find-bin.js ranks first
#
# Requires: uv, python3+pip+setuptools+packaging, a built website/dist.
# Wine is optional (runtime smoke). Does NOT run msiexec / kiro-cli MSI.
# Does NOT invent a packaged PATH fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ELECTRON_DIR="$ROOT/website/electron"
OUT="$ELECTRON_DIR/backend-dist/efm-go-backend"
PBS_KEY="${PBS_KEY:-cpython-3.12-windows-x86_64-none}"
PBS_PATTERN="${PBS_PATTERN:-cpython-3.12*-windows-x86_64-none}"
WORK="${WORK:-/tmp/efm-wp34-win-backend}"
export PYTHONNOUSERSITE=1
export PYTHONPATH=
export KIROCREW_SKIP_FRONTEND=1

log() { printf '\n\033[1;36m▶ %s\033[0m\n' "$*"; }

if [ "$(uname -s)" = "Darwin" ]; then
  echo "ERROR: this script is the Linux cross-stager. On macOS/Windows run: bash packaging/build-desktop.sh" >&2
  exit 1
fi

command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is required" >&2; exit 1; }
python3 -m pip --version >/dev/null || { echo "ERROR: python3 pip is required" >&2; exit 1; }
[ -f "$ROOT/website/dist/index.html" ] || {
  echo "ERROR: website/dist/index.html missing — build the dashboard first (cd website && npm run build)" >&2
  exit 1
}

mkdir -p "$WORK"

log "Provisioning Windows PBS via uv ($PBS_KEY)…"
uv python install "$PBS_KEY" >/dev/null || true
PBS_DIR="$(find "$(uv python dir)" -maxdepth 1 -type d -name "$PBS_PATTERN" 2>/dev/null | sort -V | tail -1)"
if [ -z "$PBS_DIR" ] || [ ! -f "$PBS_DIR/python.exe" ]; then
  echo "ERROR: no Windows PBS matching $PBS_PATTERN under $(uv python dir)" >&2
  exit 1
fi
echo "    PBS: $PBS_DIR"

log "Staging interpreter at $OUT…"
rm -rf "$OUT"
mkdir -p "$(dirname "$OUT")"
# uv plants a Linux symlink named `python` next to python.exe; do not pack it.
rsync -a \
  --exclude 'python' \
  --exclude 'python3' \
  --exclude 'python3.*' \
  "$PBS_DIR/" "$OUT/"
find "$OUT" -name "EXTERNALLY-MANAGED" -delete 2>/dev/null || true
[ -f "$OUT/python.exe" ] || { echo "ERROR: python.exe missing after rsync" >&2; exit 1; }

log "Building kirocrew py3-none-any wheel on Linux…"
rm -rf "$WORK/wheels"
mkdir -p "$WORK/wheels"
python3 -m pip wheel --no-deps --no-build-isolation -w "$WORK/wheels" "$ROOT"
WHEEL="$(ls -1 "$WORK/wheels"/kirocrew-*.whl | head -1)"
[ -n "$WHEEL" ] && [ -f "$WHEEL" ] || { echo "ERROR: kirocrew wheel not built" >&2; exit 1; }
echo "    wheel: $WHEEL"

log "Resolving Windows install_requires (markers as win32)…"
REQS="$WORK/requirements-win.txt"
python3 - "$ROOT/setup.cfg" "$REQS" <<'PY'
import sys
from pathlib import Path
from setuptools.config.setupcfg import read_configuration
from packaging.requirements import Requirement

setup_cfg, out_path = sys.argv[1], sys.argv[2]
cfg = read_configuration(setup_cfg)
reqs = cfg["options"]["install_requires"]
win_env = {
    "os_name": "nt",
    "sys_platform": "win32",
    "platform_machine": "AMD64",
    "platform_system": "Windows",
    "platform_python_implementation": "CPython",
    "python_version": "3.12",
    "python_full_version": "3.12.14",
    "implementation_name": "cpython",
    "implementation_version": "3.12.14",
}
lines = []
for raw in reqs:
    req = Requirement(raw)
    if req.marker is not None and not req.marker.evaluate(win_env):
        continue
    extras = f"[{','.join(sorted(req.extras))}]" if req.extras else ""
    lines.append(f"{req.name}{extras}{req.specifier}")
Path(out_path).write_text("\n".join(lines) + "\n")
print("\n".join(lines))
PY

sp="$OUT/Lib/site-packages"
mkdir -p "$sp"

log "Installing Windows wheels into Lib/site-packages…"
python3 -m pip install \
  --target "$sp" \
  --platform win_amd64 \
  --python-version 312 \
  --implementation cp \
  --abi cp312 \
  --only-binary=:all: \
  --no-compile \
  --upgrade \
  -r "$REQS"

log "Installing kirocrew wheel (no deps)…"
python3 -m pip install --target "$sp" --no-deps --no-compile --upgrade "$WHEEL"

log "Staging dashboard dist into efm_go/static/dist…"
mkdir -p "$sp/efm_go/static"
rm -rf "$sp/efm_go/static/dist"
cp -R "$ROOT/website/dist" "$sp/efm_go/static/dist"
[ -f "$sp/efm_go/static/dist/index.html" ] || {
  echo "ERROR: dashboard dist not staged" >&2
  exit 1
}

if [ -x "$ROOT/scripts/stamp-distribution.sh" ]; then
  bash "$ROOT/scripts/stamp-distribution.sh" source "$sp/efm_go" || true
fi

log "Writing relocatable bin/kirocrew.cmd launcher…"
mkdir -p "$OUT/bin"
printf '@echo off\r\n"%%~dp0..\\python.exe" -s -P -m efm_go %%*\r\n' > "$OUT/bin/kirocrew.cmd"
chmod +x "$OUT/bin/kirocrew.cmd"

log "Pruning bundle…"
(
  cd "$OUT"
  find . -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
  find Lib/site-packages -type d \( -name tests -o -name test \) -prune -exec rm -rf {} + 2>/dev/null || true
  rm -rf Lib/test Lib/idlelib Lib/tkinter Lib/turtledemo Lib/ensurepip Lib/lib2to3 \
         include libs tcl \
         Lib/site-packages/efm_go/_vendor/llama_cpp_libs/linux_aarch64 \
         Lib/site-packages/efm_go/_vendor/llama_cpp_libs/linux_x86_64 \
         Lib/site-packages/efm_go/_vendor/llama_cpp_libs/macos_arm64 \
         Lib/site-packages/efm_go/_vendor/llama_cpp_libs/macos_x86_64 \
         2>/dev/null || true
  rm -f DLLs/_tkinter.pyd DLLs/tcl*.dll DLLs/tk*.dll 2>/dev/null || true
)

if command -v node >/dev/null 2>&1; then
  log "Verifying bundle-integrity.js stdlib probes…"
  node -e '
    const fs=require("fs"), path=require("path");
    const { findMissingBundleParts } =
      require(path.join(process.argv[1], "bundle-integrity"));
    const missing = findMissingBundleParts(fs, path, process.argv[2]);
    if (missing.length) {
      console.error("ERROR: stdlib probes missing: " + missing.join(", "));
      process.exit(1);
    }
    console.log("    stdlib probes OK");
  ' "$ELECTRON_DIR" "$OUT"
fi

if command -v wine >/dev/null 2>&1; then
  export WINEPREFIX="${WINEPREFIX:-/tmp/efm-wine-wp34}"
  export WINEDEBUG="${WINEDEBUG:--all}"
  log "Wine smoke: python.exe -m efm_go --version…"
  mkdir -p "$WINEPREFIX"
  if wine "$OUT/python.exe" -s -P -m efm_go --version; then
    echo "    wine efm_go --version OK"
  else
    echo "    WARN: wine could not run efm_go --version (CopyFile2/other). The Windows host still runs python.exe natively."
  fi
fi

rm -f "$ELECTRON_DIR/backend-dist/README.txt"

echo
echo "    backend size: $(du -sh "$OUT" | cut -f1)"
echo "    launcher: $OUT/bin/kirocrew.cmd"
echo "    interpreter: $OUT/python.exe"
echo
log "Windows backend staged. Pack with:"
echo "    cd website/electron && npm run dist:win:portable"
echo "Native Windows (preferred): bash packaging/build-desktop.sh"
