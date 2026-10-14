"""Multi-provider MCP server discovery and installation.

This package provides a pluggable interface for searching and installing
MCP servers from external registries. Each provider (official MCP registry,
an edition capability backend, etc.) implements the ``McpProvider`` protocol and registers itself in
the ``ProviderRegistry`` — the same shape as ``efm_go.skill_providers``.
"""

from efm_go.mcp_providers.base import (
    McpInstallPlan,
    McpProvider,
    McpSearchResult,
    McpServerDetail,
    ProviderRegistry,
    ProviderUnavailableError,
)
from efm_go.mcp_providers.capability import CapabilityProvider
from efm_go.mcp_providers.official import OfficialRegistryProvider

__all__ = [
    "CapabilityProvider",
    "McpInstallPlan",
    "McpProvider",
    "McpSearchResult",
    "McpServerDetail",
    "OfficialRegistryProvider",
    "ProviderRegistry",
    "ProviderUnavailableError",
]
