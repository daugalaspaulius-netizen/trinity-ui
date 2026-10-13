#!/usr/bin/env python3
"""EFM Backup — round-trip and negative test suite.

Exercises:
- Portable Backup creation (sessions included, secrets excluded)
- Secret leak detection
- Vendor config sanitization
- Restore (sessions return, integrations marked reauth)
- Negative tests (corrupt archive, wrong checksum, path traversal, etc.)
- Safety snapshot encryption
- Pre-update hook

Run: .venv-test/bin/python tests/test_efm_backup.py
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kiro_crew.efm_backup import (
    SECRETS_INVENTORY,
    VENDOR_ENDPOINT_PATTERNS,
    check_backup_content,
    create_portable_backup,
    create_safety_snapshot,
    create_test_fixture,
    pre_update_hook,
    restore_portable_backup,
    sanitize_vendor_config,
    _validate_backup_archive,
)

PASS = 0
FAIL = 0
RESULTS = []


def report(name: str, passed: bool, detail: str = ""):
    global PASS, FAIL
    status = "PASS" if passed else "FAIL"
    if passed:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append((name, status, detail))
    print(f"[{status}] {name}" + (f" — {detail}" if detail else ""))


def main():
    tmp = Path(tempfile.mkdtemp(prefix="efm-test-"))

    # ============================================================
    # STEP A: Create fixture
    # ============================================================
    fixture_dir = tmp / "profile"
    fixture = create_test_fixture(str(fixture_dir))
    report("Fixture created", fixture_dir.exists(), f"{fixture_dir}")

    # ============================================================
    # STEP B: Portable Backup
    # ============================================================
    archive = str(tmp / "backup.tar.gz")
    ok, path, manifest = create_portable_backup(
        archive, source_sha="test-sha-123", data_dir=str(fixture_dir)
    )
    report("Portable Backup created", ok, path)
    report("Manifest has format_version", manifest.get("format_version") == "efm-portable-1")
    report("Manifest has checksum", bool(manifest.get("checksum")))
    report("Manifest has sessions_count", "sessions_count" in manifest)

    # ============================================================
    # STEP B checks: content present
    # ============================================================
    content = check_backup_content(path)
    report("Sessions in backup", content["sessions_found"])
    report("Memory in backup", content["memory_found"])
    report("Skills in backup", content["skills_found"])
    report("Schedule in backup", content["schedule_found"])
    report("Settings in backup", content["settings_found"])
    report("Manifest in backup", content["manifest_found"])

    # ============================================================
    # STEP B checks: secrets ABSENT
    # ============================================================
    report(
        "No API keys in backup",
        not any(s["class"] == "api_keys" for s in content["secrets_found"]),
        str(content["secrets_found"]),
    )
    report(
        "No OAuth tokens in backup",
        not any(s["class"] == "oauth_tokens" for s in content["secrets_found"]),
    )
    report(
        "No cookies in backup",
        not any(s["class"] == "browser_cookies" for s in content["secrets_found"]),
    )
    report(
        "No OpenZiti identities in backup",
        not any(s["class"] == "openziti_identities" for s in content["secrets_found"]),
    )
    report(
        "No HMAC keys in backup",
        not any(s["class"] == "hmac_signing_keys" for s in content["secrets_found"]),
    )
    report("No program binaries in backup", not content["program_binary_found"])

    # Verify no secret files physically in archive
    secret_files = []
    with tarfile.open(path, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if any(
                x in name.lower()
                for x in ["key.txt", "oauth", "cookie", "ziti", "hmac", "sel_hmac"]
            ):
                secret_files.append(name)
    report("No secret files physically present", not secret_files, str(secret_files))

    # ============================================================
    # Vendor endpoints sanitized
    # ============================================================
    report(
        "No Kiro vendor endpoints in backup",
        not content["vendor_endpoints_found"],
        str(content["vendor_endpoints_found"]),
    )

    # ============================================================
    # STEP C: Clean profile
    # ============================================================
    clean_dir = tmp / "clean_profile"
    clean_dir.mkdir()
    report("Clean profile created", clean_dir.exists())

    # ============================================================
    # STEP D: Restore
    # ============================================================
    ok, result = restore_portable_backup(path, target_data_home=str(clean_dir))
    report("Restore succeeded", ok, str(result.get("error", "")))
    report("Restore restored files", result.get("restored_files", 0) > 0, str(result.get("restored_files")))

    # ============================================================
    # STEP E: Check restored content
    # ============================================================
    report(
        "Sessions restored",
        (clean_dir / "sessions" / "chat-001.jsonl").exists(),
    )
    report(
        "Memory restored",
        (clean_dir / "memory.db").exists(),
    )
    report(
        "Skills restored",
        (clean_dir / "skills" / "test-skill" / "SKILL.md").exists(),
    )
    report(
        "Schedule restored",
        (clean_dir / "crons.json").exists(),
    )
    report(
        "Artifacts restored",
        (clean_dir / "artifacts" / "test-artifact" / "file.txt").exists(),
    )
    report(
        "Reauth marker created",
        (clean_dir / "reauth_required.json").exists(),
    )

    # Check config sanitized
    if (clean_dir / "config.json").exists():
        cfg_text = (clean_dir / "config.json").read_text()
        report(
            "Kiro vendor endpoints NOT restored",
            "crew.kiro.dev" not in cfg_text,
        )

    # ============================================================
    # Safety snapshot
    # ============================================================
    safety = str(tmp / "safety.efm.safety")
    ok, safety_path, safety_manifest = create_safety_snapshot(
        safety, trigger="BEFORE_RESTORE", data_dir=str(fixture_dir)
    )
    report("Safety snapshot created", ok, safety_path)
    report("Safety snapshot encrypted", safety_manifest.get("encrypted") is True)
    # Verify NOT plaintext
    with open(safety_path, "rb") as f:
        raw = f.read()
    report(
        "Safety snapshot not plaintext",
        b"safety" not in raw[:100] and "memory-db-content".encode() not in raw,
    )

    # ============================================================
    # Pre-update hook
    # ============================================================
    ok, hook_path = pre_update_hook(str(fixture_dir))
    report("Pre-update hook created snapshot", ok, hook_path)

    # ============================================================
    # Negative tests
    # ============================================================
    # 1. Corrupt archive
    corrupt = tmp / "corrupt.tar.gz"
    corrupt.write_text("this is not a tar file")
    valid, msg = _validate_backup_archive(str(corrupt))
    report("Corrupt archive REFUSED", not valid, msg)

    # 2. Path traversal archive (with valid manifest, so traversal is what's caught)
    traversal = tmp / "traversal.tar.gz"
    with tarfile.open(str(traversal), "w:gz") as tar:
        manifest_data = json.dumps({"format_version": "efm-portable-1"}).encode()
        mi = tarfile.TarInfo(name="MANIFEST.json")
        mi.size = len(manifest_data)
        tar.addfile(mi, fileobj=io.BytesIO(manifest_data))
        data = b"malicious"
        info = tarfile.TarInfo(name="../etc/passwd")
        info.size = len(data)
        tar.addfile(info, fileobj=io.BytesIO(data))
    valid, msg = _validate_backup_archive(str(traversal))
    report("Path traversal REFUSED", not valid and "traversal" in msg.lower(), msg)

    # 3. Program binary archive (with valid manifest)
    binary_archive = tmp / "binary.tar.gz"
    with tarfile.open(str(binary_archive), "w:gz") as tar:
        manifest_data = json.dumps({"format_version": "efm-portable-1"}).encode()
        mi = tarfile.TarInfo(name="MANIFEST.json")
        mi.size = len(manifest_data)
        tar.addfile(mi, fileobj=io.BytesIO(manifest_data))
        data = b"MZ..."
        info = tarfile.TarInfo(name="app.asar")
        info.size = len(data)
        tar.addfile(info, fileobj=io.BytesIO(data))
    valid, msg = _validate_backup_archive(str(binary_archive))
    report("Program binary REFUSED", not valid and "binary" in msg.lower(), msg)

    # 4. Missing manifest
    no_manifest = tmp / "nomanifest.tar.gz"
    with tarfile.open(str(no_manifest), "w:gz") as tar:
        data = b"some data"
        info = tarfile.TarInfo(name="file.txt")
        info.size = len(data)
        tar.addfile(info, fileobj=None)
    valid, msg = _validate_backup_archive(str(no_manifest))
    report("Missing manifest REFUSED", not valid, msg)

    # 5. Vendor sanitize function
    test_config = {
        "beacon_enabled": True,
        "update_feed_url": "https://updates.crew.kiro.dev",
        "keep_me": "value",
        "nested": {"catalog_endpoint": "https://apps.crew.kiro.dev", "keep": True},
    }
    cleaned = sanitize_vendor_config(test_config)
    report(
        "Vendor sanitize strips keys",
        "beacon_enabled" not in cleaned and "update_feed_url" not in cleaned,
        str(cleaned),
    )
    report(
        "Vendor sanitize keeps user keys",
        "keep_me" in cleaned and cleaned["keep_me"] == "value",
    )
    report(
        "Vendor sanitize recurses nested",
        "catalog_endpoint" not in cleaned.get("nested", {}),
    )

    # 6. Secret path detection
    from kiro_crew.efm_backup import is_secret_path
    is_sec, name = is_secret_path("config.local.json")
    report("Secret path detection: config.local.json", is_sec and name == "api_keys")
    is_sec, name = is_secret_path("workspace/my_doc.md")
    report("Non-secret path: workspace doc", not is_sec)

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print(f"TOTAL: {PASS} PASS, {FAIL} FAIL")
    print("=" * 60)

    shutil.rmtree(tmp, ignore_errors=True)

    if FAIL > 0:
        print("\nFAILED TESTS:")
        for name, status, detail in RESULTS:
            if status == "FAIL":
                print(f"  - {name}: {detail}")
        sys.exit(1)
    else:
        print("\nALL TESTS PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
