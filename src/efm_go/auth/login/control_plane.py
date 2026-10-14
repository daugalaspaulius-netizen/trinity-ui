"""Profile listing for an old enterprise sign-in.

The management hosts and the profile POST are gone. A caller that still asks
gets a loud error instead of a stored credential that points at a foreign service.
"""

from __future__ import annotations

from dataclasses import dataclass


class ControlPlaneError(Exception):
    """Profile resolution is disconnected."""


@dataclass
class KiroProfile:
    arn: str
    profile_name: str


def control_plane_url(region: str) -> str:
    raise ControlPlaneError("EFM Go disconnected the profile service.")


async def list_available_profiles(
    access_token: str, *, region: str, session: object
) -> list[KiroProfile]:
    raise ControlPlaneError("EFM Go disconnected the profile service.")
