#!/usr/bin/env python3
"""Precise 'Kiro Crew' → 'EFM Go' replacement based on inventory token ranges.
Only modifies USER_VISIBLE_RENAME tokens. Handles multi-line tokens."""

import os, re, json, sys

INVENTORY = "/opt/efm/kirocrew-ui/backend-brand-inventory.json"

data = json.load(open(INVENTORY))

rename_records = [r for r in data['records'] if r['class'] == 'USER_VISIBLE_RENAME']
rewire_records = [r for r in data['records'] if r['action'] == 'REWIRE' and r['class'] == 'VENDOR_REWIRE_REMOVE']

# Group by file
from collections import defaultdict
by_file = defaultdict(list)
for rec in rename_records:
    by_file[rec['path']].append(rec)

# Also handle VENDOR rewires
vendor_by_file = defaultdict(list)
for rec in rewire_records:
    vendor_by_file[rec['path']].append(rec)

total_rename = 0
total_vendor = 0

# ============ PART 1: USER_VISIBLE_RENAME ============
print("=== USER_VISIBLE_RENAME ===")
for relpath, records in sorted(by_file.items()):
    filepath = os.path.join("/opt/efm/kirocrew-ui", relpath)
    if not os.path.exists(filepath):
        print(f"  SKIP {relpath} (missing)")
        continue
    
    with open(filepath, "r", errors="replace") as fh:
        content = fh.read()
        lines = content.split("\n")
    
    modified = False
    # Build list of (line_num, col_start, col_end, old_str, new_str)
    # for each occurrence within the token ranges
    replacements = []
    
    for rec in records:
        token_start_line = rec['line_start']
        token_start_col = rec['col_start']
        token_end_line = rec.get('line_end', token_start_line)
        token_end_col = rec.get('col_end', len(lines[-1]) if token_end_line >= len(lines) else len(lines[token_end_line-1]))
        
        # Find ALL "Kiro Crew" occurrences within this token range
        for line_i in range(token_start_line - 1, min(token_end_line, len(lines))):
            line = lines[line_i]
            for m in re.finditer(r'Kiro Crew', line):
                col = m.start()
                # Check if within this token's range
                if line_i == token_start_line - 1 and col < token_start_col:
                    continue
                if line_i == token_end_line - 1 and col + len('Kiro Crew') > token_end_col:
                    continue
                if line_i < token_start_line - 1 or line_i > token_end_line - 1:
                    continue
                replacements.append((line_i, col, col + len('Kiro Crew')))
    
    if not replacements:
        continue
    
    # Apply replacements in reverse order
    new_lines = list(lines)
    for line_i, col_start, col_end in sorted(replacements, reverse=True):
        line = new_lines[line_i]
        new_lines[line_i] = line[:col_start] + "EFM Go" + line[col_end:]
        total_rename += 1
        modified = True
    
    if modified:
        new_content = "\n".join(new_lines)
        with open(filepath, "w") as fh:
            fh.write(new_content)
        print(f"  RENAMED {len(replacements)} in {relpath}")

# ============ PART 2: VENDOR_ENDPOINT rewires ============
print("\n=== VENDOR_REWIRE_REMOVE ===")

vendor_fixes = {
    "src/efm_go/platform/update_layout.py": [
        ('return "https://updates.crew.kiro.dev", "https://download.crew.kiro.dev"',
         'return "", ""'),
    ],
    "src/efm_go/apps/official_catalog.py": [
        ('OFFICIAL_CATALOG_BASE = "https://apps.crew.kiro.dev/"',
         'OFFICIAL_CATALOG_BASE = "https://efmleads.com/api/apps/"'),
    ],
    "src/efm_go/diagnostics.py": [
        ('_ISSUE_REPO = "kirodotdev/KiroCrew"',
         '_ISSUE_REPO = "efmleads/efm-go"'),
    ],
    "src/efm_go/cloud/ec2.py": [
        ('PUBLIC_REPO_URL = "https://github.com/kirodotdev/KiroCrew.git"',
         'PUBLIC_REPO_URL = "https://github.com/efmleads/efm-go.git"'),
    ],
    "src/efm_go/service/linux.py": [
        ('"Documentation=https://github.com/kirodotdev/KiroCrew\\n"',
         '"Documentation=https://github.com/efmleads/efm-go\\n" # EFM'),
    ],
    "src/efm_go/doctor_checks/access.py": [
        ('"https://github.com/kirodotdev/KiroCrew/blob/main/src/efm_go/docs/blocked-commands.md"',
         '"https://github.com/efmleads/efm-go/blob/main/docs/blocked-commands.md"'),
    ],
    "src/efm_go/sandbox.py": [
        ('kirodotdev/KiroCrew/main/docker/seccomp/kirocrew-seccomp.json',
         'efmleads/efm-go/main/docker/seccomp/efm-go-seccomp.json'),
    ],
}

for relpath, fixes in sorted(vendor_fixes.items()):
    filepath = os.path.join("/opt/efm/kirocrew-ui", relpath)
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r") as fh:
        content = fh.read()
    
    modified = False
    for old, new in fixes:
        if old in content:
            content = content.replace(old, new)
            total_vendor += 1
            modified = True
        else:
            print(f"  WARN {relpath}: '{old[:50]}...' not found")
    
    if modified:
        with open(filepath, "w") as fh:
            fh.write(content)
        print(f"  REWIRED {len(fixes)} in {relpath}")

# ============ SUMMARY ============
print(f"\n=== SUMMARY ===")
print(f"  USER_VISIBLE_RENAME (Kiro Crew → EFM Go): {total_rename} occurrences")
print(f"  VENDOR endpoint rewires: {total_vendor} occurrences")

# ============ POST-CLEAN VERIFY ============
print("\n=== POST-CLEAN VERIFICATION ===")
# Recount "Kiro Crew" in user-visible files
remaining_uv = 0
for relpath in sorted(by_file.keys()):
    filepath = os.path.join("/opt/efm/kirocrew-ui", relpath)
    if not os.path.exists(filepath):
        continue
    with open(filepath) as fh:
        content = fh.read()
    # Count "Kiro Crew" — these should now be only in docstrings/comments, NOT in user-visible strings
    count = content.count("Kiro Crew")
    if count > 0:
        # Check: are these in strings or comments?
        lines = content.split("\n")
        for i, line in enumerate(lines, 1):
            if "Kiro Crew" in line:
                # Only show if preceded by a quote (still in a string)
                stripped = line.strip()
                if '"' in stripped or "'" in stripped:
                    print(f"  REMAINING: {relpath}:{i}: {line.strip()[:80]}")
                    remaining_uv += 1

if remaining_uv == 0:
    print("  ALL user-visible 'Kiro Crew' replaced! ✓")
else:
    print(f"  WARNING: {remaining_uv} 'Kiro Crew' remain in string context!")

# Also verify vendor endpoints
remaining_vendor = 0
for relpath in sorted(vendor_fixes.keys()):
    filepath = os.path.join("/opt/efm/kirocrew-ui", relpath)
    if not os.path.exists(filepath):
        continue
    with open(filepath) as fh:
        content = fh.read()
    for old, new in vendor_fixes[relpath]:
        if old in content:
            print(f"  VENDOR REMAINING: {relpath}: {old[:60]}...")
            remaining_vendor += 1
if remaining_vendor == 0:
    print("  All vendor endpoints rewired! ✓")

sys.exit(0)