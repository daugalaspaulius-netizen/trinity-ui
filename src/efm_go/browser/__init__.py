"""Gateway-side plumbing for the native embedded browser panel.

Holds the loopback command bus (:mod:`efm_go.browser.command_bus`) that
bridges the agent's ``browser`` MCP tool to the Electron main process, which
owns the embedded ``WebContentsView`` and drives it over in-process CDP.
"""
