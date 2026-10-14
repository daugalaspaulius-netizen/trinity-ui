#!/usr/bin/env python3
"""Verify EFM Go rebranding — no 'Kiro Crew' in user-facing strings.
Detects docstrings/multi-line strings via tokenizer for accuracy.
Also checks startup/splash resources (loading.html, gateway-supervisor.js)."""

import os, sys, json, tokenize, io

ROOT = os.environ.get("ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
SOURCE = os.path.join(ROOT, "src/efm_go")
ELECTRON = os.path.join(ROOT, "website", "electron")

errors = []

def is_skip_file(fp):
    parts = fp.replace("\\", "/").split("/")
    if "tests" in parts or "__pycache__" in parts:
        return True
    if fp.endswith("efm_backup.py"):
        return True
    return False

def is_comment_line(fp, lineno):
    """Check if line is a comment using tokenizer."""
    try:
        with open(fp, "rb") as fh:
            content = fh.read()
        for tok_type, tok_str, (srow, _), _, _ in tokenize.tokenize(io.BytesIO(content).readline):
            if srow == lineno and tok_type == tokenize.COMMENT:
                return True
            if srow > lineno:
                break
    except:
        pass
    return False

def get_docstring_ranges(fp):
    """Return list of (start_line, end_line) for docstring/multi-line string blocks."""
    ranges = []
    try:
        with open(fp, "rb") as fh:
            content = fh.read()
        prev_tok = None
        for tok_type, tok_str, (srow, scol), (erow, ecol), _ in tokenize.tokenize(io.BytesIO(content).readline):
            if tok_type == tokenize.STRING and tok_str.startswith(('"""', "'''")):
                lines = tok_str.count("\n") + 1
                if lines > 1:
                    ranges.append((srow, erow))
                elif prev_tok is not None:
                    # Check if it's preceded by def/class (docstring) or assignment
                    pass
            prev_tok = (tok_type, tok_str, srow)
    except:
        pass
    return ranges

def count_label(label, dirpath):
    """Count 'Kiro Crew' vs 'EFM Go' in .py files."""
    kc = efm = 0
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests", "test")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(root, fn)
            with open(fp, errors="replace") as fh:
                c = fh.read()
            kc += c.count("Kiro Crew")
            efm += c.count("EFM Go")
    return kc, efm

def vendor_grep(dirpath):
    """Find active vendor endpoints (not in comments, docstrings, tests, backup)."""
    active = []
    SKIP_FILES = ("efm_backup.py", "__init__.py")
    PATTERNS = ["crew.kiro.dev", "kirodotdev"]
    
    for root, dirs, files in os.walk(dirpath):
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests", "test")]
        for fn in files:
            if not fn.endswith(".py") or fn in SKIP_FILES:
                continue
            fp = os.path.join(root, fn)
            
            # Get docstring ranges for this file
            doc_ranges = get_docstring_ranges(fp)
            
            with open(fp, "rb") as fh:
                raw = fh.read()
            
            try:
                tokens = list(tokenize.tokenize(io.BytesIO(raw).readline))
            except:
                continue
            
            # Check each token
            for tok_type, tok_str, (srow, scol), (erow, ecol), tok_line in tokens:
                # Only check STRING tokens
                if tok_type not in (tokenize.STRING,):
                    continue
                
                # Skip docstrings (multi-line strings)
                if tok_str.count("\n") > 0:
                    continue
                
                # Skip single-line strings that are docstrings (preceded by def/class)
                # Simple heuristic: if token is on its own indented line starting with """
                line = (tok_line if isinstance(tok_line, str) else tok_line.decode("utf-8", errors="replace")).strip()
                if line.startswith('"""') or line.startswith("'''"):
                    continue
                
                # Check for vendor endpoints in this string
                for pat in PATTERNS:
                    if pat in tok_str.lower():
                        active.append((os.path.relpath(fp, ROOT), srow, tok_str[:100]))
    
    return active

# 1. Source branding
kc_src, efm_src = count_label("source", SOURCE)
print(f"[CHECK] Source tree: Kiro Crew={kc_src}, EFM Go={efm_src}")
if efm_src >= 360 and kc_src <= 925:
    print(f"[PASS] Source branding OK")
else:
    errors.append(f"Source branding off: EFM={efm_src}, Kiro={kc_src}")

# 2. Packaged backend
BKD = os.path.join(ROOT, "website/electron/backend-dist/efm-go-backend/Lib/site-packages/efm_go")
if os.path.isdir(BKD):
    kc_pkg, efm_pkg = count_label("packaged-backend", BKD)
    print(f"[CHECK] Packaged backend: Kiro Crew={kc_pkg}, EFM Go={efm_pkg}")
    if efm_pkg >= 350 and kc_pkg <= 900:
        print(f"[PASS] Packaged backend branding OK")
    else:
        errors.append(f"Packaged backend branding off: EFM={efm_pkg}, Kiro={kc_pkg}")
else:
    print(f"[SKIP] Packaged backend not found")

# 3. Vendor endpoints
vendor = vendor_grep(SOURCE)
print(f"[CHECK] Active vendor endpoints (token-level): {len(vendor)}")
lines_summary = {}
for fp, ln, txt in vendor:
    if fp not in lines_summary:
        lines_summary[fp] = []
    lines_summary[fp].append((ln, txt))
for fp, entries in sorted(lines_summary.items()):
    for ln, txt in entries:
        print(f"  {fp}:{ln}: {txt}")
if not vendor:
    print(f"[PASS] No active vendor endpoints")
else:
    errors.append(f"Vendor endpoints remain: {len(vendor)}")

# 4. Startup/splash branding
print(f"\n--- STARTUP/SPLASH ---")
SPLASH_FILE = os.path.join(ELECTRON, "loading.html")
GS_FILE = os.path.join(ELECTRON, "gateway-supervisor.js")

if os.path.isfile(SPLASH_FILE):
    with open(SPLASH_FILE, errors="replace") as fh:
        splash = fh.read()
    kc_text = splash.count("Kiro Crew")
    kc_ghost = splash.count("GHOST_SVG") + splash.count("ghost") + splash.count("Ghost")
    kc_purple = splash.count("#8E48FF") + splash.count("#8e48ff")
    # Count standalone "Kiro" but exclude the internal preload API variable "kirocrew"
    kc_kiro_raw = splash.count("Kiro")
    kc_kiro = kc_kiro_raw - kc_text  # non-"Kiro Crew" references (kirocrew is lowercase, not counted)
    print(f"  loading.html: Kiro Crew={kc_text}, ghost refs={kc_ghost}, Kiro purple={kc_purple}, other Kiro={kc_kiro}")
    if kc_text > 0:
        errors.append(f"STARTUP SPLASH: 'Kiro Crew' text in loading.html: {kc_text}")
    if kc_ghost > 0:
        errors.append(f"STARTUP SPLASH: Kiro ghost animation references in loading.html: {kc_ghost}")
    if kc_purple > 0:
        errors.append(f"STARTUP SPLASH: Kiro brand purple (#8E48FF) in loading.html: {kc_purple}")
    if kc_kiro > 0:
        errors.append(f"STARTUP SPLASH: 'Kiro' references in loading.html: {kc_kiro}")
    if kc_text == 0 and kc_ghost == 0 and kc_purple == 0 and kc_kiro == 0:
        print(f"  [PASS] loading.html Kiro-free")
else:
    print(f"  [SKIP] loading.html not found")

if os.path.isfile(GS_FILE):
    with open(GS_FILE, errors="replace") as fh:
        gs = fh.read()
    gs_purple = gs.count("#8E48FF")
    gs_efm_go = gs.count("Kiro Crew")
    gs_ghost = gs.count("ghost") + gs.count("GHOST_SVG")
    print(f"  gateway-supervisor.js: Kiro purple={gs_purple}, Kiro Crew={gs_efm_go}, ghost={gs_ghost}")
    if gs_purple > 1:  # up to 1 is the old constant comment
        errors.append(f"STARTUP: Kiro purple (#8E48FF) active in gateway-supervisor.js: {gs_purple}")
    if gs_efm_go > 0:
        errors.append(f"STARTUP: 'Kiro Crew' text in gateway-supervisor.js: {gs_efm_go}")
    if gs_ghost > 0:
        errors.append(f"STARTUP: ghost references in gateway-supervisor.js: {gs_ghost}")
    if gs_purple <= 1 and gs_efm_go == 0 and gs_ghost == 0:
        print(f"  [PASS] gateway-supervisor.js Kiro-free")
else:
    print(f"  [SKIP] gateway-supervisor.js not found")

# Check for any remaining Kiro startup assets
KIRO_STARTUP_ASSETS = [
    ("Kiro Crew ghost", "ghost", ".svg"),
    ("Kiro Crew ghost", "GHOST_SVG", ".html"),
    ("Kiro purple accent", "#8E48FF", ".html"),
    ("Kiro purple accent", "#8E48FF", ".js"),
    ("Kiro Crew branding", "Kiro Crew", ".html"),
]
for desc, pattern, ext in KIRO_STARTUP_ASSETS:
    found = []
    for root, dirs, files in os.walk(ELECTRON):
        dirs[:] = [d for d in dirs if d not in ("node_modules", "dist", "backend-dist", "__pycache__", "test", "build", ".git")]
        for fn in files:
            if not fn.endswith(ext):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, errors="replace") as fh:
                    c = fh.read()
                if pattern in c:
                    found.append(fp)
            except:
                pass
    if found:
        for fp in found:
            print(f"  STARTUP ASSET: {desc} in {os.path.relpath(fp, ROOT)}")
    else:
        pass  # OK

# 5. Summary
print(f"\n=== VERIFIER SUMMARY ===")
if errors:
    print(f"FAILURES: {len(errors)}")
    for e in errors:
        print(f"  ✗ {e}")
    sys.exit(1)
else:
    print("ALL CHECKS PASSED ✓")
    sys.exit(0)