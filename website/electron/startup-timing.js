"use strict";
/* Startup timing instrumentation — development only, logs to stderr.
   Collects monotonic timestamps (performance.now / Date.now)
   from EXE click through to usable UI. */

var t = Object.create(null);
var _origin = Date.now();
var _started = false;

var ipcMain = null;

function stamp(key) {
  var ms = Date.now();
  t[key] = { ms: ms, elapsed: ms - _origin };
  console.error("[startup-timing] " + key + " " + t[key].elapsed + "ms");
  return t[key];
}

function dump() {
  var keys = Object.keys(t);
  if (keys.length === 0) { console.error("[startup-timing] (no stamps recorded)"); return; }
  console.error("[startup-timing] === STAMP DUMP ===");
  keys.forEach(function(k) {
    console.error("[startup-timing]   " + k + ": +" + t[k].elapsed + "ms");
  });
  console.error("[startup-timing] === END DUMP ===");
}

function init() {
  if (_started) return;
  _started = true;
  _origin = Date.now();
  stamp("T0_process_start");
}

function initIpc(ipc) {
  ipcMain = ipc;
  if (!ipcMain) return;
  ipcMain.on("startup-timing", function(_event, key) {
    if (typeof key === "string" && key) stamp(key);
  });
}

module.exports = {
  stamp: stamp,
  dump: dump,
  init: init,
  initIpc: initIpc,
  get: function(k) { return t[k]; },
  getAll: function() { return t; },
};