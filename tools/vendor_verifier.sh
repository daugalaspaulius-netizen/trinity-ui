#!/usr/bin/env bash
# Vendor endpoint verifier: ensure no active Kiro vendor endpoints in code.
# "Active" = a real STRING token in executable code (not comment, not docstring,
# not efm_backup.py sanitization list). Uses Python tokenize (same as brand_verifier.py)
# to avoid false positives on multi-line docstring continuation lines.
set -euo pipefail

ROOT="${1:-/opt/efm/kirocrew-ui}"
SRC="$ROOT/src/kiro_crew"

python3 - "$ROOT" "$SRC" <<'PYEOF'
import os, sys, io, tokenize

ROOT, SRC = sys.argv[1], sys.argv[2]
SKIP_FILES = ("efm_backup.py", "__init__.py")
PATTERNS = ["crew.kiro.dev", "kirodotdev"]

def get_docstring_ranges(fp):
    ranges = []
    try:
        with open(fp, "rb") as fh:
            raw = fh.read()
        tokens = list(tokenize.tokenize(io.BytesIO(raw).readline))
    except Exception:
        return ranges
    for tok in tokens:
        if tok.type == tokenize.STRING and tok.string.startswith(('"""', "'''")):
            ranges.append((tok.start[0], tok.end[0]))
    return ranges

active = []
for root, dirs, files in os.walk(SRC):
    dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests", "test")]
    for fn in files:
        if not fn.endswith(".py") or fn in SKIP_FILES:
            continue
        fp = os.path.join(root, fn)
        doc_ranges = get_docstring_ranges(fp)
        with open(fp, "rb") as fh:
            raw = fh.read()
        try:
            tokens = list(tokenize.tokenize(io.BytesIO(raw).readline))
        except Exception:
            continue
        for tok in tokens:
            if tok.type != tokenize.STRING:
                continue
            srow, erow = tok.start[0], tok.end[0]
            # skip docstrings (multi-line or single-line on def/class)
            if tok.string.count("\n") > 0:
                continue
            if any(a <= srow <= b for a, b in doc_ranges):
                continue
            for pat in PATTERNS:
                if pat in tok.string.lower():
                    active.append(f"{os.path.relpath(fp, ROOT)}:{srow}: {tok.string[:100]}")

print("=== VENDOR VERIFIER ===")
print(f"Source: {SRC}")
print()
if active:
    for a in active:
        print(f"  ACTIVE VENDOR: {a}")
    print()
    print(f"FAIL: Active vendor endpoints remain ({len(active)})!")
    sys.exit(1)
else:
    print("PASS: No active vendor endpoints (token-level, docstring-aware).")
    sys.exit(0)
PYEOF
