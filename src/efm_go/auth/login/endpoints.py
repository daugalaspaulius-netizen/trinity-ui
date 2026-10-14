"""EFM Go auth constants.

Portal, social sign-in, OIDC, and Builder ID start addresses are disconnected.
Sign-in for the product is efmleads.com.
"""

from __future__ import annotations

# Loopback ports kept so an old local callback listener still binds.
CALLBACK_PORTS: tuple[int, ...] = (
    3128,
    4649,
    6588,
    8008,
    9091,
    49153,
    50153,
    51153,
    52153,
    53153,
)

BUILDER_ID_REGION = ""
BUILDER_ID_START_URL = ""
AMZN_START_URL = ""
OIDC_SCOPES: tuple[str, ...] = ()
OIDC_CLIENT_NAME = "EFM Go"
USER_AGENT = "EFM-Go"
DEFAULT_TOKEN_TTL_SECS = 3600


def portal_url() -> str:
    raise RuntimeError("EFM Go disconnected portal. Sign-in is efmleads.com.")


def social_service_url() -> str:
    raise RuntimeError("EFM Go disconnected social service. Sign-in is efmleads.com.")


def oidc_url(region: str) -> str:
    raise RuntimeError("EFM Go disconnected OIDC.")
