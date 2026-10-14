"""Local-desktop Founder flag. Never used by the public website/BFF."""
from __future__ import annotations

import os
from pathlib import Path

_TRUE = frozenset({"1", "true", "yes", "on"})


def is_local_founder() -> bool:
    """True when this process is the installed Founder desktop gateway.

    Electron sets ``EFM_GO_LOCAL_FOUNDER=1``. A marker file at
    ``~/.kiro/crew/.efm_local_founder`` is the offline equivalent.
    Public BFF/website auth does not read this helper.
    """
    flag = os.environ.get("EFM_GO_LOCAL_FOUNDER", "").strip().lower()
    if flag in _TRUE:
        return True
    try:
        return (Path.home() / ".kiro" / "crew" / ".efm_local_founder").is_file()
    except OSError:
        return False
