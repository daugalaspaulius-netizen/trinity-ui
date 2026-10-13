"use strict";
// Fail a Windows electron-builder pack when extraResources would ship an
// empty/placeholder backend-dist. Packaged apps refuse PATH fallback
// (gateway-supervisor.js), so a missing launcher means a permanent loading.html.
//
// Wired as package.json build.beforePack. Also runnable as:
//   node scripts/assert-bundled-backend.js

const fs = require("fs");
const path = require("path");

const ELECTRON_DIR = path.join(__dirname, "..");

const REQUIRED_WINDOWS_BACKEND = [
  ["backend-dist", "kirocrew-backend", "python.exe"],
  ["backend-dist", "kirocrew-backend", "bin", "kirocrew.cmd"],
];

function assertWindowsBackend(electronDir = ELECTRON_DIR) {
  const missing = REQUIRED_WINDOWS_BACKEND
    .map((parts) => path.join(electronDir, ...parts))
    .filter((p) => !fs.existsSync(p))
    .map((p) => path.relative(electronDir, p).split(path.sep).join("/"));
  if (missing.length === 0) return;
  const placeholder = path.join(electronDir, "backend-dist", "README.txt");
  const hint = fs.existsSync(placeholder)
    ? " backend-dist/README.txt is a placeholder, not a backend."
    : "";
  throw new Error(
    "Windows pack refused: bundled backend missing (" +
      missing.join(", ") +
      ")." +
      hint +
      " Stage website/electron/backend-dist/kirocrew-backend via packaging/build-desktop.sh (native Windows) or packaging/build-windows-backend-on-linux.sh (Linux+Wine), then re-run electron-builder --win. Packaged apps do not fall back to PATH."
  );
}

async function beforePack(context) {
  if (!context || context.electronPlatformName !== "win32") return;
  assertWindowsBackend(ELECTRON_DIR);
}

exports.default = beforePack;
exports.assertWindowsBackend = assertWindowsBackend;

if (require.main === module) {
  try {
    assertWindowsBackend();
    process.stdout.write("bundled Windows backend OK\n");
  } catch (err) {
    process.stderr.write(String(err && err.message ? err.message : err) + "\n");
    process.exit(1);
  }
}
