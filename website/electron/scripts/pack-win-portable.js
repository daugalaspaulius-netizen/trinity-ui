"use strict";
// Linux pack of the Windows portable SFX. electron-builder otherwise shells
// out to Wine signtool after the payload is already written, which hangs on
// this host (same Wine kernel32 class as NSIS). CSC_IDENTITY_AUTO_DISCOVERY=false
// matches packaging/build-desktop.sh and ships unsigned, which is required
// here — there is no Windows signing secret.
const { spawnSync } = require("child_process");
const path = require("path");

process.env.CSC_IDENTITY_AUTO_DISCOVERY = "false";
const eb = path.join(__dirname, "..", "node_modules", ".bin", "electron-builder");
const r = spawnSync(eb, ["--win", "portable", "--publish", "never", "--config.compression=normal"], {
  stdio: "inherit",
  env: process.env,
});
process.exit(r.status === null ? 1 : r.status);
