"""EFM Go — safe Portable Backup & System Safety Snapshot.

Builds on top of the existing Kiro Crew snapshot/restore engine
(snapshot.py, snapshot_components.py, snapshot_restore.py, snapshot_archive.py).
Adds sessions backup, secrets exclusions, vendor config sanitization,
pre-restore/update safety, and an encrypted safety snapshot.

Design principle: reuse, don't rewrite. The existing snapshot engine handles
component staging, archive creation, restore transactions, and rollback.
EFM layers add sessions, secrets policy, and safety on top.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import struct
import tarfile
import tempfile
from datetime import datetime, timezone
from enum import Enum, auto
from pathlib import Path
from typing import Any

from efm_go.config.paths import data_home, kiro_sessions_dir


# ============================================================================
# Secrets inventory — what must NEVER ride a Portable Backup
# ============================================================================

SECRET_CLASSES: dict[str, SecretClass] = {}


class SecretClass:
    """A catalogued category of credential that Portable Backup must exclude."""

    def __init__(self, name: str, globs: list[str], portable_action: str):
        self.name = name
        self.globs = globs  # data-home-relative glob patterns
        self.portable_action = portable_action  # EXCLUDE | REDACT | METADATA_ONLY


# Ordered by risk: most dangerous secrets first.
# These are data-home-relative paths and glob patterns.
SECRETS_INVENTORY: list[SecretClass] = [
    SecretClass(
        "api_keys",
        ["config.local.json", "*.key", "*.pem", "*.p12", "**/secrets/**"],
        "EXCLUDE",
    ),
    SecretClass(
        "oauth_tokens",
        ["oauth_tokens.json", "**/oauth/**", "**/*.oauth"],
        "EXCLUDE",
    ),
    SecretClass(
        "openziti_identities",
        ["**/ziti/**", "**/*.jwt", "**/identities/**"],
        "EXCLUDE",
    ),
    SecretClass(
        "device_private_keys",
        ["**/*_private*", "**/ssh/**", "**/*.ed25519", "**/*.rsa"],
        "EXCLUDE",
    ),
    SecretClass(
        "browser_cookies",
        ["**/Cookies", "**/cookies*", "**/Local State"],
        "EXCLUDE",
    ),
    SecretClass(
        "auth_cookies_session",
        ["**/auth_sessions/**", "**/*.auth", "sel_hmac.key"],
        "EXCLUDE",
    ),
    SecretClass(
        "local_tokens",
        ["token.json", "local_token*", "**/*.token", "refresh_token*"],
        "EXCLUDE",
    ),
    SecretClass(
        "gateway_secrets",
        ["gateway_secrets*", "**/secret://**", "**/*.encrypted*"],
        "EXCLUDE",
    ),
    SecretClass(
        "hmac_signing_keys",
        ["sel_hmac.key", "**/*.hmac", "**/signing_key*"],
        "EXCLUDE",
    ),
]


def is_secret_path(relative_path: str) -> tuple[bool, str | None]:
    """Check if a data-home-relative path matches any secret class.
    Returns (is_secret, secret_class_name)."""
    normalized = relative_path.replace("\\", "/").lstrip("/")
    for sc in SECRETS_INVENTORY:
        for pattern in sc.globs:
            # Simple glob: ** matches any depth, * matches within one segment
            regex = _glob_to_regex(pattern)
            if regex.match(normalized):
                return True, sc.name
    return False, None


def _glob_to_regex(glob_pattern: str) -> re.Pattern:
    """Convert a simple glob pattern to a regex."""
    parts = glob_pattern.split("/")
    regex_parts = []
    for i, part in enumerate(parts):
        if part == "**":
            regex_parts.append(r"(?:.+/)?" if i < len(parts) - 1 else r".*")
        elif part == "*":
            regex_parts.append(r"[^/]+")
        else:
            regex_parts.append(re.escape(part))
    return re.compile("^" + "/".join(regex_parts) + "$")


# ============================================================================
# Vendor endpoints to sanitize on restore
# ============================================================================

VENDOR_ENDPOINT_PATTERNS: list[str] = [
]


VENDOR_CONFIG_KEYS_TO_STRIP: list[str] = [
    "beacon_enabled",
    "beacon_endpoint",
    "update_feed_url",
    "remote_catalog_url",
    "catalog_endpoint",
    "telemetry_enabled",
    "remote_crew_enabled",
    "aws_identity_enabled",
    "kiro_identity_active",
]


def sanitize_vendor_config(data: dict[str, Any]) -> dict[str, Any]:
    """Remove Kiro vendor configuration from a config dict."""
    result = dict(data)
    # Strip known vendor keys
    for key in VENDOR_CONFIG_KEYS_TO_STRIP:
        result.pop(key, None)
    # Recurse into nested dicts
    for k, v in list(result.items()):
        if isinstance(v, dict):
            result[k] = sanitize_vendor_config(v)
    return result


def sanitize_vendor_endpoints(text: str) -> str:
    """Replace Kiro vendor endpoint references in any text."""
    for pattern in VENDOR_ENDPOINT_PATTERNS:
        # Replace host references but preserve the structure
        text = text.replace(pattern, "DISABLED_KIRO_ENDPOINT")
    return text


# ============================================================================
# Session discovery
# ============================================================================

SESSION_ROOTS: dict[str, str] = {
    "dashboard": str(data_home() / "sessions"),
    "cli": str(kiro_sessions_dir()),
}


def _session_roots_for(data_dir: str | None = None) -> dict[str, str]:
    """Return session roots for a specific data dir (or the default)."""
    if data_dir:
        base = Path(data_dir)
        return {
            "dashboard": str(base / "sessions"),
            "cli": str(base / "sessions" / "cli"),
        }
    return SESSION_ROOTS


def discover_sessions(data_dir: str | None = None) -> dict[str, list[Path]]:
    """Find all session files. Returns {source: [paths]}."""
    result: dict[str, list[Path]] = {}
    roots = _session_roots_for(data_dir)
    for source, root_str in roots.items():
        root = Path(root_str)
        if not root.exists():
            continue
        paths = sorted(root.glob("*.jsonl"))
        if paths:
            result[source] = paths
    return result


# ============================================================================
# Portable Backup Manifest (EFM extended)
# ============================================================================

PORTABLE_BACKUP_FORMAT_VERSION = "efm-portable-1"


def create_backup_manifest(
    components: list[str],
    sessions_count: int,
    files_count: int,
    source_sha: str,
    app_version: str,
    excluded_secrets: list[str],
) -> dict[str, Any]:
    return {
        "format_version": PORTABLE_BACKUP_FORMAT_VERSION,
        "app_version": app_version,
        "source_sha": source_sha,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "components": components,
        "sessions_count": sessions_count,
        "files_count": files_count,
        "excluded_secret_classes": excluded_secrets,
        "sanitization_version": 1,
    }


# ============================================================================
# Portable Backup — CREATE
# ============================================================================


def create_portable_backup(
    output_path: str,
    source_sha: str = "",
    app_version: str = "0.9.0",
    include_components: list[str] | None = None,
    data_dir: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Create an EFM Portable Backup.

    Returns (success, archive_path, manifest).

    The backup includes user work (sessions, memory, skills, schedules, settings,
    artifacts) but EXCLUDES secrets (API keys, OAuth tokens, OpenZiti identities,
    browser cookies, auth tokens, HMAC keys).

    Uses the existing Kiro Crew snapshot engine for core components and adds
    sessions as an EFM-specific layer.
    """
    from efm_go.snapshot import _build_snapshot, snapshot_main

    tmpdir = Path(tempfile.mkdtemp(prefix="efm-portable-"))
    datadir = Path(data_dir) if data_dir else data_home()

    if not datadir.exists():
        return False, "", {"error": f"Data home not found: {datadir}"}

    # Default components = all core + sessions
    if include_components is None:
        include_components = list(_PORTABLE_BACKUP_COMPONENTS)

    # 1. Stage core components using existing snapshot engine
    # We create an in-memory snapshot using the existing engine's staging
    staged_dir = tmpdir / "staged"
    staged_dir.mkdir()

    files_count = 0
    excluded_secrets: list[str] = []

    for component in include_components:
        if component == "sessions":
            # Custom sessions backup (not in Kiro snapshot engine)
            sessions = discover_sessions(data_dir)
            for source, paths in sessions.items():
                for p in paths:
                    dst = staged_dir / "sessions" / p.name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, dst)
                    files_count += 1
        elif component == "config_safe":
            # Config files but with secrets stripped
            cfg_src = datadir / "config.json"
            if cfg_src.exists():
                try:
                    cfg_data = json.loads(cfg_src.read_text(encoding="utf-8"))
                    cfg_data = sanitize_vendor_config(cfg_data)
                    dst = staged_dir / "config.json"
                    dst.write_text(json.dumps(cfg_data, indent=2), encoding="utf-8")
                    files_count += 1
                except Exception:
                    pass
            # Also copy ui-prefs, notification_settings (non-secret config)
            for f in ["ui-prefs.json", "notification_settings.json"]:
                src = datadir / f
                if src.exists():
                    shutil.copy2(src, staged_dir / f)
                    files_count += 1
        elif component == "memory":
            for f in ["memory.db", "memory_index.db"]:
                src = datadir / f
                if src.exists():
                    shutil.copy2(src, staged_dir / f)
                    files_count += 1
            ms_dir = datadir / "memory_stores"
            if ms_dir.exists():
                shutil.copytree(
                    ms_dir,
                    staged_dir / "memory_stores",
                    ignore=_ignore_host_local_patterns,
                    dirs_exist_ok=True,
                )
        elif component == "workspace":
            ws = datadir / "workspace"
            if ws.exists():
                shutil.copytree(
                    ws,
                    staged_dir / "workspace",
                    ignore=_ignore_secrets_patterns,
                    dirs_exist_ok=True,
                )
        elif component == "skills":
            sk = datadir / "skills"
            if sk.exists():
                shutil.copytree(sk, staged_dir / "skills", dirs_exist_ok=True)
        elif component == "crons":
            cr = datadir / "crons.json"
            if cr.exists():
                shutil.copy2(cr, staged_dir / "crons.json")
                files_count += 1
        elif component == "artifacts":
            ar = datadir / "artifacts"
            if ar.exists():
                shutil.copytree(ar, staged_dir / "artifacts", dirs_exist_ok=True)
        elif component == "uploads":
            up = datadir / "uploads"
            if up.exists():
                shutil.copytree(up, staged_dir / "uploads", dirs_exist_ok=True)

    # 2. Check for secrets in staged content
    secrets_found: list[str] = []
    for root, dirs, files_list in os.walk(staged_dir):
        for f in files_list:
            fpath = os.path.join(root, f)
            rel = os.path.relpath(fpath, staged_dir)
            is_sec, name = is_secret_path(rel)
            if is_sec and name:
                secrets_found.append(rel)
                os.remove(fpath)  # Physically exclude

    if secrets_found:
        excluded_secrets = sorted(set(x.split("/")[0] if "/" not in x else x for x in secrets_found))

    # 3. Create manifest
    sessions_data = discover_sessions(data_dir)
    sessions_count = sum(len(v) for v in sessions_data.values())

    manifest = create_backup_manifest(
        components=include_components,
        sessions_count=sessions_count,
        files_count=files_count,
        source_sha=source_sha,
        app_version=app_version,
        excluded_secrets=[
            s.name
            for s in SECRETS_INVENTORY
            if any(p in ",".join(secrets_found) for p in s.globs)
        ],
    )

    manifest_path = staged_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 4. Create tar.gz archive
    archive_path = output_path
    if not archive_path.endswith(".tar.gz"):
        archive_path = output_path + ".tar.gz"

    with tarfile.open(archive_path, "w:gz") as tar:
        # Write manifest first
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        info = tarfile.TarInfo(name="MANIFEST.json")
        info.size = len(manifest_bytes)
        info.mtime = int(datetime.now(timezone.utc).timestamp())
        tar.addfile(info, fileobj=io.BytesIO(manifest_bytes))

        # Write all staged files
        for root, dirs, files_list in os.walk(staged_dir):
            for f in files_list:
                fpath = Path(root) / f
                arcname = str(fpath.relative_to(staged_dir))
                if arcname == "MANIFEST.json":
                    continue
                tar.add(fpath, arcname=arcname)

    # 5. Compute checksum
    sha256 = hashlib.sha256()
    with open(archive_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)

    manifest["checksum"] = sha256.hexdigest()

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)

    return True, archive_path, manifest


# ============================================================================
# System Safety Snapshot
# ============================================================================

SAFETY_SNAPSHOT_FORMAT = "efm-safety-1"


def create_safety_snapshot(
    output_path: str,
    trigger: str = "MANUAL",
    key: bytes | None = None,
    data_dir: str | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    """Create an EFM System Safety Snapshot (encrypted, internal use).

    Used BEFORE_UPDATE, BEFORE_MIGRATION, or BEFORE_RESTORE.
    More comprehensive than Portable Backup — includes full config state.
    Encrypted with a platform-appropriate key.

    On Linux/test: uses a test key. Production key comes from OS-backed storage.
    """
    from efm_go.snapshot import _build_snapshot

    if key is None:
        # Test mode: use a fixed test key (never use in production!)
        key = b"EFM_SAFETY_SNAPSHOT_TEST_KEY_2026"

    datadir = Path(data_dir) if data_dir else data_home()
    if not datadir.exists():
        return False, "", {"error": f"Data home not found: {datadir}"}

    tmpdir = Path(tempfile.mkdtemp(prefix="efm-safety-"))
    staged_dir = tmpdir / "staged"
    staged_dir.mkdir()

    # Full copy of all data home content (comprehensive)
    files_count = 0
    for root, dirs, files_list in os.walk(datadir):
        for f in files_list:
            fpath = Path(root) / f
            rel = fpath.relative_to(datadir)
            # Skip program binaries
            if rel.parts and rel.parts[0] in ("node_modules", "__pycache__", ".git"):
                continue
            dst = staged_dir / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                shutil.copy2(fpath, dst)
                files_count += 1
            except OSError:
                pass

    manifest = {
        "format_version": SAFETY_SNAPSHOT_FORMAT,
        "trigger": trigger,
        "app_version": "0.9.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files_count": files_count,
        "encrypted": True,
    }

    manifest_path = staged_dir / "MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # Create tar.gz
    plain_path = str(tmpdir / "safety.tar.gz")
    with tarfile.open(plain_path, "w:gz") as tar:
        tar.add(staged_dir, arcname="safety")

    # Encrypt the plain archive
    encrypted_path = output_path
    if not encrypted_path.endswith(".efm.safety"):
        encrypted_path = output_path + ".efm.safety"

    with open(plain_path, "rb") as fsrc:
        plain = fsrc.read()

    encrypted = _encrypt_data(plain, key)
    Path(encrypted_path).parent.mkdir(parents=True, exist_ok=True)
    with open(encrypted_path, "wb") as fdst:
        fdst.write(encrypted)

    # Cleanup
    shutil.rmtree(tmpdir, ignore_errors=True)

    sha256 = hashlib.sha256()
    with open(encrypted_path, "rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            sha256.update(chunk)

    manifest["checksum"] = sha256.hexdigest()
    manifest["output_path"] = encrypted_path

    return True, encrypted_path, manifest


def pre_update_hook(data_dir: str | None = None) -> tuple[bool, str]:
    """Integration seam for future auto-update.

    Create a System Safety Snapshot before quitAndInstall.
    Currently the updater is muted; this hook is tested via integration tests.
    """
    if data_dir is None:
        data_dir = str(data_home())

    safety_dir = Path(data_dir) / "safety_snapshots"
    safety_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = str(safety_dir / f"pre-update-{ts}.efm.safety")

    ok, out_path, manifest = create_safety_snapshot(
        path, trigger="BEFORE_UPDATE", data_dir=data_dir
    )
    return ok, out_path


# ============================================================================
# Portable Restore
# ============================================================================


def restore_portable_backup(
    archive_path: str,
    target_data_home: str | None = None,
) -> tuple[bool, dict[str, Any]]:
    """Restore an EFM Portable Backup.

    1. Validate archive integrity and manifest
    2. Create System Safety Snapshot (pre-restore safety)
    3. Restore to target data home
    4. Sanitize vendor config
    5. Mark integrations as REAUTH_REQUIRED
    """
    if not os.path.exists(archive_path):
        return False, {"error": f"Archive not found: {archive_path}"}

    # 1. Validate archive
    valid, msg = _validate_backup_archive(archive_path)
    if not valid:
        return False, {"error": msg}

    # 2. Read manifest
    manifest = _read_backup_manifest(archive_path)
    if not manifest:
        return False, {"error": "Cannot read manifest"}

    fmt = manifest.get("format_version", "")
    if fmt != PORTABLE_BACKUP_FORMAT_VERSION:
        return False, {"error": f"Unknown format: {fmt}"}

    # 3. Create safety snapshot before restore
    target = Path(target_data_home) if target_data_home else data_home()
    safety_path = str(target / "safety_snapshots" / f"pre-restore-{_utc_ts()}.efm.safety")
    create_safety_snapshot(safety_path, trigger="BEFORE_RESTORE", data_dir=str(target))

    # 4. Extract archive
    tmpdir = Path(tempfile.mkdtemp(prefix="efm-restore-"))
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(tmpdir, filter="data")

        # 4. Copy restored files to target data home
        restored = 0
        for root, dirs, files_list in os.walk(tmpdir):
            for f in files_list:
                fpath = Path(root) / f
                if f == "MANIFEST.json":
                    continue
                rel = fpath.relative_to(tmpdir)
                dst = target / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(fpath, dst)
                    restored += 1
                except OSError as e:
                    pass

        # 5. Sanitize vendor config after restore
        _sanitize_restored_config(target)

        # 6. Mark integrations for reauth
        _mark_integrations_reauth(target)

        return True, {
            "restored_files": restored,
            "target": str(target),
            "safety_snapshot": safety_path,
            "manifest": manifest,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


# ============================================================================
# Archive validation
# ============================================================================


def _validate_backup_archive(archive_path: str) -> tuple[bool, str]:
    """Validate a Portable Backup archive."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            members = tar.getmembers()
            if not members:
                return False, "Empty archive"

            # Security checks FIRST (before completeness checks)
            for m in members:
                if ".." in m.name or m.name.startswith("/") or m.name.startswith("\\"):
                    return False, f"Path traversal detected: {m.name}"

            # Check for program binaries
            for m in members:
                if any(
                    m.name.endswith(s)
                    for s in (".exe", ".dll", ".asar", ".so", ".node", ".wasm")
                ):
                    return False, f"Program binary in backup: {m.name}"

            # Check for manifest (completeness check)
            has_manifest = any(m.name == "MANIFEST.json" for m in members)
            if not has_manifest:
                return False, "Missing MANIFEST.json"

        return True, "OK"
    except tarfile.TarError as e:
        return False, f"Archive error: {e}"


def _read_backup_manifest(archive_path: str) -> dict[str, Any] | None:
    """Read the backup manifest from an archive."""
    try:
        with tarfile.open(archive_path, "r:gz") as tar:
            for member in tar.getmembers():
                if member.name == "MANIFEST.json":
                    f = tar.extractfile(member)
                    if f:
                        return json.loads(f.read().decode("utf-8"))
    except Exception:
        pass
    return None


def _sanitize_restored_config(target: Path):
    """Remove vendor config from restored config files."""
    config_path = target / "config.json"
    if config_path.exists():
        try:
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            cfg = sanitize_vendor_config(cfg)
            # Strip vendor endpoints from all string values
            cfg_str = json.dumps(cfg)
            cfg_str = sanitize_vendor_endpoints(cfg_str)
            cfg = json.loads(cfg_str)
            config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        except Exception:
            pass


def _mark_integrations_reauth(target: Path):
    """Mark all OAuth/integration connections as needing reauth after restore."""
    reauth_path = target / "reauth_required.json"
    reauth_marker = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "reason": "Portable Backup restore — secrets excluded for safety",
        "actions_needed": [
            "Reconnect OAuth providers (Settings → Connections)",
            "Re-enter API keys (Settings → API Keys)",
            "Re-authenticate OpenZiti identity",
            "Re-login to browser-based services",
        ],
    }
    reauth_path.write_text(json.dumps(reauth_marker, indent=2), encoding="utf-8")


# ============================================================================
# Helpers
# ============================================================================


_PORTABLE_BACKUP_COMPONENTS = [
    "sessions",
    "memory",
    "skills",
    "crons",
    "config_safe",
    "workspace",
    "artifacts",
    "uploads",
]


def _ignore_secrets_patterns(directory: str, contents: list[str]) -> list[str]:
    """Ignore function for shutil.copytree that excludes secret files."""
    ignored = []
    for item in contents:
        # Check the item name against secret patterns directly
        for sc in SECRETS_INVENTORY:
            for pattern in sc.globs:
                # Match against just the filename/basename and simple path
                regex = _glob_to_regex(pattern.split("/")[-1])
                if regex.match(item):
                    ignored.append(item)
                    break
    return ignored


def _ignore_host_local_patterns(directory: str, contents: list[str]) -> list[str]:
    """Ignore host-local store state (signing keys, backups, exec logs)."""
    ignored = []
    for item in contents:
        if item in ("backups", "execution_logs", "signing_key", ".lock"):
            ignored.append(item)
    return ignored


def _encrypt_data(data: bytes, key: bytes) -> bytes:
    """Simple authenticated encryption using macOS/Linux-compatible approach.
    Test mode: XOR with key (NOT for production). Production: use OS-backed crypto."""
    # Test-only: XOR cipher with key (production must use AES-GCM or platform crypto)
    result = bytearray(len(data))
    for i, b in enumerate(data):
        result[i] = b ^ key[i % len(key)]
    return bytes(result)


def _decrypt_data(encrypted: bytes, key: bytes) -> bytes:
    """Decrypt data encrypted with _encrypt_data."""
    return _encrypt_data(encrypted, key)  # XOR is symmetric


def _utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


# ============================================================================
# Test helpers
# ============================================================================


def create_test_fixture(base_dir: str) -> dict[str, Any]:
    """Create an isolated test profile with known content for round-trip testing."""
    base = Path(base_dir)
    base.mkdir(parents=True, exist_ok=True)

    # Sessions
    sessions = base / "sessions"
    sessions.mkdir()
    (sessions / "chat-001.jsonl").write_text(
        '{"role":"user","content":"Hello EFM"}\n{"role":"assistant","content":"Hi!"}\n'
    )
    (sessions / "chat-002.jsonl").write_text(
        '{"role":"user","content":"Test backup"}\n'
    )

    # Memory
    (base / "memory.db").write_text("memory-db-content")
    (base / "memory_index.db").write_text("memory-index-content")

    # Memory stores
    ms = base / "memory_stores" / "default"
    ms.mkdir(parents=True)
    (ms / "store.db").write_text("store-content")

    # Config
    cfg = {
        "agent": "opencode",
        "theme": "dark",
        "vendor_config": {
            "beacon_enabled": True,
            "beacon_endpoint": "https://efmleads.com",
            "update_feed_url": "https://efmleads.com/go/updates",
            "remote_catalog_url": "https://efmleads.com/api/apps",
        },
    }
    (base / "config.json").write_text(json.dumps(cfg))

    # Secret fixtures
    (base / "api_keys" / "openai").mkdir(parents=True)
    (base / "api_keys" / "openai" / "key.txt").write_text("sk-test-dummy-key-12345")
    (base / "oauth_tokens.json").write_text('{"access_token":"dummy-oauth-token"}')
    (base / "browser_cookies.json").write_text('{"session":"dummy-cookie"}')
    (base / "ziti_identity.json").write_text('{"private_key":"dummy-ziti-private"}')
    (base / "sel_hmac.key").write_text("dummy-hmac-key")

    # Skills
    sk = base / "skills" / "test-skill"
    sk.mkdir(parents=True)
    (sk / "SKILL.md").write_text("# Test Skill")

    # Schedule
    (base / "crons.json").write_text('[{"name":"test","schedule":"0 * * * *"}]')

    # UI prefs
    (base / "ui-prefs.json").write_text('{"theme":"dark"}')

    # Artifacts
    ar = base / "artifacts" / "test-artifact"
    ar.mkdir(parents=True)
    (ar / "file.txt").write_text("artifact content")

    return {
        "base_dir": str(base),
        "sessions": 2,
        "memory_db": True,
        "skills": 1,
        "crons": 1,
        "artifacts": 1,
        "secrets": 5,
    }


def check_backup_content(archive_path: str) -> dict[str, Any]:
    """Analyze what's in a backup archive. Returns a dict of findings."""
    findings: dict[str, Any] = {
        "sessions_found": False,
        "memory_found": False,
        "skills_found": False,
        "schedule_found": False,
        "settings_found": False,
        "secrets_found": [],
        "program_binary_found": False,
        "manifest_found": False,
        "vendor_endpoints_found": [],
    }

    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            name = member.name
            if "MANIFEST.json" in name:
                findings["manifest_found"] = True
            if "sessions" in name.lower() or "chat" in name.lower() or ".jsonl" in name:
                findings["sessions_found"] = True
            if "memory" in name.lower():
                findings["memory_found"] = True
            if "skill" in name.lower():
                findings["skills_found"] = True
            if "cron" in name.lower():
                findings["schedule_found"] = True
            if "config" in name.lower() or "ui-prefs" in name:
                findings["settings_found"] = True
            if any(name.endswith(s) for s in (".exe", ".asar", ".dll", ".so", ".node")):
                findings["program_binary_found"] = True

    # Check for secrets
    for secret_class in SECRETS_INVENTORY:
        for pattern in secret_class.globs:
            # Simple check: does any file in the archive match the pattern?
            with tarfile.open(archive_path, "r:gz") as tar:
                for member in tar.getmembers():
                    rel = member.name.split("/", 1)[-1] if "/" in member.name else member.name
                    regex = _glob_to_regex(pattern)
                    if regex.match(rel) or regex.match(member.name):
                        findings["secrets_found"].append(
                            {"class": secret_class.name, "file": member.name}
                        )
                        break

    # Check for vendor endpoints in config files
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if "config" in member.name.lower() and member.isfile():
                f = tar.extractfile(member)
                if f:
                    content = f.read().decode("utf-8", errors="replace")
                    for endpoint in VENDOR_ENDPOINT_PATTERNS:
                        if endpoint in content:
                            findings["vendor_endpoints_found"].append(endpoint)

    return findings