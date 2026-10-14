"""KAS-mode auth subsystem.

Performs the full Kiro OIDC lifecycle (interactive login, refresh, secure storage,
identity classification) for the KAS-embedded runtime, where there is no kiro-cli to
delegate auth to. The resulting token is fed to the embedded ``@kiro/agent`` (KAS)
engine through the ``IAuthProvider`` contract (or the ``_kiro/auth/getAccessToken``
acp-callback).

See docs/system-specs/modules/kas-auth.md for the full design.
"""

from __future__ import annotations

from efm_go.auth.provider import KasAuthProvider, NotAuthenticated
from efm_go.auth.shape import InstallShape, Transport, detect_shape, select_transport
from efm_go.auth.store import KasToken, SocialProvider, TokenStore

__all__ = [
    "KasToken",
    "SocialProvider",
    "TokenStore",
    "KasAuthProvider",
    "NotAuthenticated",
    "InstallShape",
    "Transport",
    "detect_shape",
    "select_transport",
]
