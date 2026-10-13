#!/usr/bin/env python3
"""Precise 'Kiro Crew' backend inventory using Python tokenizer — v2."""

import os, re, json, sys, tokenize, io
from collections import Counter

SRC = "/opt/efm/kirocrew-ui/src/kiro_crew"
OUT = "/opt/efm/kirocrew-ui/backend-brand-inventory.json"

def classify_token(tok_type, tok_str, relpath):
    """Classify based on token type."""
    basename = os.path.basename(relpath)
    is_test = ('/tests/' in relpath or '/test/' in relpath or 
               basename.startswith('test_') or basename.endswith('_test.py') or 
               basename == 'conftest.py')
    
    if is_test:
        return "TEST_DOC_ONLY"
    
    if tok_type == tokenize.COMMENT:
        return "TEST_DOC_ONLY"
    
    if tok_type in (tokenize.STRING, tokenize.FSTRING_MIDDLE if hasattr(tokenize, 'FSTRING_MIDDLE') else -1):
        sv = tok_str.lower()
        if any(d in sv for d in ["crew.kiro.dev", "kirodotdev"]):
            return "VENDOR_REWIRE_REMOVE"
        if any(k in sv for k in ["license", "notice", "copyright", "apache"]):
            return "LICENSE_NOTICE_KEEP"
        # Docstring (triple-quoted) — these reference "Kiro Crew" as documentation
        if '"""' in tok_str or "'''" in tok_str:
            return "TEST_DOC_ONLY"
        return "USER_VISIBLE_RENAME"
    
    if tok_type in (tokenize.NAME, tokenize.NUMBER):
        return "INTERNAL_COMPAT_KEEP"
    
    return "UNKNOWN"

def scan():
    records = []
    total = 0
    by_class = Counter()
    files_with_hits = set()
    
    for root, dirs, files in os.walk(SRC):
        for fn in sorted(files):
            if not fn.endswith(".py"):
                continue
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, "/opt/efm/kirocrew-ui")
            
            try:
                with open(fp, "rb") as fh:
                    content = fh.read()
                
                if b"Kiro Crew" not in content:
                    continue
                
                tokens = list(tokenize.tokenize(io.BytesIO(content).readline))
                
                for tok_type, tok_str, (srow, scol), (erow, ecol), tok_line in tokens:
                    if tok_type in (tokenize.ENDMARKER, tokenize.NEWLINE, tokenize.NL, tokenize.INDENT, tokenize.DEDENT, tokenize.ENCODING):
                        continue
                    
                    # Check if "Kiro Crew" is in this token
                    str_val = tok_str if isinstance(tok_str, str) else tok_str.decode("utf-8", errors="replace")
                    if "Kiro Crew" not in str_val:
                        continue
                    
                    # Count occurrences within this token
                    count = str_val.count("Kiro Crew")
                    
                    klass = classify_token(tok_type, str_val, rel)
                    action = {
                        "USER_VISIBLE_RENAME": "RENAME",
                        "VENDOR_REWIRE_REMOVE": "REWIRE",
                        "INTERNAL_COMPAT_KEEP": "KEEP_COMPAT",
                        "LICENSE_NOTICE_KEEP": "KEEP_LICENSE",
                        "TEST_DOC_ONLY": "KEEP_TEST_DOC",
                        "UNKNOWN": "UNKNOWN",
                    }[klass]
                    
                    records.append({
                        "path": rel,
                        "line_start": srow,
                        "col_start": scol,
                        "line_end": erow,
                        "col_end": ecol,
                        "tok_type": tokenize.tok_name.get(tok_type, str(tok_type)),
                        "tok_preview": str_val[:80],
                        "count_in_token": count,
                        "class": klass,
                        "action": action,
                    })
                    total += count
                    by_class[klass] += count
                    files_with_hits.add(rel)
                    
            except Exception as e:
                print(f"ERR {rel}: {e}")
    
    result = {
        "meta": {
            "generated": "2026-10-12T10:00:00Z",
            "source_dir": SRC,
            "total_occurrences": total,
            "total_files": len(files_with_hits),
            "by_class": dict(sorted(by_class.items())),
        },
        "records": sorted(records, key=lambda x: (x["path"], x["line_start"])),
    }
    
    sum_check = sum(by_class.values())
    assert sum_check == total, f"SUM MISMATCH: {sum_check} != {total}"
    
    json.dump(result, open(OUT, "w"), indent=2, ensure_ascii=False)
    
    print(f"TOTAL: {total} occurrences in {len(files_with_hits)} files")
    for k, v in sorted(by_class.items()):
        print(f"  {k}: {v}")
    print(f"  Sum: {sum_check}")
    print(f"Output: {OUT}\n")

if __name__ == "__main__":
    scan()
    sys.exit(0)