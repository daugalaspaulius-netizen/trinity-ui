"""Owner-only ACLs for credential leaves. Never world-readable."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def lock_credential_paths(paths=None) -> None:
    """Restrict credential files/dirs to the current user only.

    Used when a local Founder desktop must run OpenCode on native Windows,
    where Crew has no OS sandbox backend to hide these leaves. Tightening
    the DACL / mode is not an OS sandbox; it just refuses world-readable
    secrets on disk.
    """
    if paths is None:
        try:
            from efm_go.security import sandbox_credential_targets
            paths = sandbox_credential_targets()
        except Exception:
            paths = ()
    for raw in paths:
        try:
            p = Path(raw)
            if not p.exists():
                continue
            if os.name == "nt":
                _lock_nt(p)
            else:
                os.chmod(p, 0o700 if p.is_dir() else 0o600)
        except OSError:
            continue


def _lock_nt(path: Path) -> None:
    user = os.environ.get("USERNAME") or os.environ.get("USER") or ""
    if not user:
        return
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    grant = f"{user}:(OI)(CI)F" if path.is_dir() else f"{user}:F"
    subprocess.run(
        ["icacls", str(path), "/inheritance:d", "/grant:r", grant],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )
    for group in ("Everyone", "Users", "Authenticated Users"):
        subprocess.run(
            ["icacls", str(path), "/remove:g", group],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
