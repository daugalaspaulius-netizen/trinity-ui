"""Dashboard API handlers for the "Report a Problem" diagnostics flow.

POST /api/diagnostics/collect          — build a redacted diagnostics bundle
GET  /api/diagnostics/download/{name}  — download a previously-built bundle

Both share the collector engine in :mod:`efm_go.diagnostics`, the exact same
code path the ``kirocrew doctor --bundle`` CLI uses. Auth + host validation are
applied globally by the dashboard middleware chain. Both handlers are also
owner-gated: a bundle carries the owner's gateway and chat logs, so only the
dashboard owner may build or download one. The blocking collect runs off the
event loop via ``asyncio.to_thread``.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import logging
import urllib.parse

from aiohttp import web

from efm_go import diagnostics
from efm_go.config.loader import config_dir
from efm_go.dashboard.handlers._shared import require_owner_dashboard_request

logger = logging.getLogger(__name__)


def _diagnostics_dir():
    return config_dir() / "diagnostics"


def _sel():
    """Late-binding sel() for test monkeypatch compatibility."""
    # circular import: the parent package `efm_go.dashboard.handlers` imports
    # this module at package-init time, so it cannot be imported at module scope
    # here. Resolving it lazily also keeps `sel` looked up on the package object
    # at call time, which is what lets tests monkeypatch `handlers.sel`.
    import efm_go.dashboard.handlers as _pkg

    return _pkg.sel()


def _audit_collect_allowed_sync(include_logs: bool) -> None:
    """Best-effort SEL record of an allowed collect; never raises.

    Blocking body of :func:`_audit_collect_allowed`: the first ``sel()`` of a
    process constructs the log, so handlers reach this through the async
    wrapper, which runs it off the event loop.
    """
    try:
        _sel().log_tool_invocation(
            session_key="api",
            source="api",
            tool_name="diagnostics_collect",
            tool_kind="collect",
            outcome="allowed",
            resources=f"include_logs={include_logs}",
        )
    except Exception:  # pragma: no cover - audit must never change the outcome
        logger.debug("SEL audit for diagnostics collect failed", exc_info=True)


async def _audit_collect_allowed(include_logs: bool) -> None:
    """Record an allowed collect without stalling the event loop."""
    try:
        await asyncio.to_thread(_audit_collect_allowed_sync, include_logs)
    except Exception:  # pragma: no cover - audit must never change the outcome
        logger.debug("SEL audit dispatch for diagnostics collect failed", exc_info=True)


async def api_diagnostics_collect(request: web.Request) -> web.Response:
    """POST /api/diagnostics/collect — collect + redact + zip diagnostics.

    Body (all optional): ``{"note": str, "include_logs": bool}``.
    Returns the bundle metadata plus a ``download_url`` and the pre-filled
    GitHub issue URL.
    """
    owner_denied = await require_owner_dashboard_request(request, "diagnostics.collect")
    if owner_denied is not None:
        return owner_denied
    try:
        body = await request.json()
    except Exception:
        body = {}
    if not isinstance(body, dict):
        return web.json_response(
            {"error": "request body must be an object", "code": "invalid_body"},
            status=400,
        )

    note = str(body.get("note") or "")
    include_logs = bool(body.get("include_logs", True))

    # The owner gate audits only its refusals; record the allowed build here,
    # before the collector reads the owner's logs.
    await _audit_collect_allowed(include_logs)
    try:
        result = await asyncio.to_thread(
            diagnostics.collect_bundle,
            note=note,
            include_logs=include_logs,
            output_dir=_diagnostics_dir(),
        )
    except Exception:  # pragma: no cover - defensive
        logger.exception("diagnostics collection failed")
        # The dashboard renders ``error`` verbatim into a localized UI, so raw
        # exception text (which can carry paths or internal detail) must not
        # reach the client. The detail stays in the server log above.
        return web.json_response(
            {"error": "collection failed", "code": "collection_failed"},
            status=500,
        )

    payload = result.as_dict()
    payload["download_url"] = "/api/diagnostics/download/" + urllib.parse.quote(
        result.filename, safe=""
    )
    return web.json_response(payload)


async def api_diagnostics_download(request: web.Request) -> web.StreamResponse:
    """GET /api/diagnostics/download/{filename} — stream a bundle zip.

    Scoped strictly to ``<data_home>/diagnostics``; path traversal and
    non-``.zip`` names are rejected. Served as ``application/zip`` directly, so
    it does not touch the shared binary-MIME allowlist.
    """
    owner_denied = await require_owner_dashboard_request(request, "diagnostics.download")
    if owner_denied is not None:
        return owner_denied
    filename = request.match_info["filename"]
    base = _diagnostics_dir().resolve()
    path = (base / filename).resolve()

    if not path.is_relative_to(base) or path.suffix != ".zip" or not path.is_file():
        _sel().log_tool_invocation(
            session_key="api",
            source="api",
            tool_name="diagnostics_download",
            tool_kind="download",
            outcome="denied",
            error=f"rejected: {filename}",
        )
        return web.json_response({"error": "forbidden", "code": "forbidden"}, status=403)

    _sel().log_tool_invocation(
        session_key="api",
        source="api",
        tool_name="diagnostics_download",
        tool_kind="download",
        outcome="allowed",
        resources=path.name,
    )
    safe_name = urllib.parse.quote(path.name, safe="")
    return web.FileResponse(
        path,
        headers={
            "Content-Type": "application/zip",
            "Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}",
            "X-Content-Type-Options": "nosniff",
        },
    )


async def api_diagnostics_send_efm(request):
    """POST /api/diagnostics/send-efm — keep zip, copy to EFM outbox. No GitHub."""
    from aiohttp import web
    import json as _json
    import shutil as _shutil
    from datetime import datetime, timezone
    try:
        body = await request.json()
    except Exception:
        body = {}
    zip_path = str(body.get("zip_path") or "")
    note = str(body.get("note") or "")
    outbox = Path.home() / ".efm-go-outbox" / "reports"
    try:
        outbox.mkdir(parents=True, exist_ok=True)
        dest = None
        if zip_path and Path(zip_path).is_file():
            dest = outbox / Path(zip_path).name
            _shutil.copy2(zip_path, dest)
        meta = outbox / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-note.txt")
        meta.write_text((note or "EFM Go report") + "\nzip=" + (str(dest) if dest else zip_path) + "\n", encoding="utf-8")
        # Optional Contabo hop through existing tunnel; never a new public port.
        url = os.environ.get("EFM_REPORT_URL", "").strip()
        if url and dest:
            try:
                import urllib.request
                data = dest.read_bytes()
                req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": "application/zip", "X-EFM-Note": note[:200]})
                urllib.request.urlopen(req, timeout=15).read()
            except Exception:
                pass
        return web.json_response({"ok": True, "outbox": str(dest or outbox)})
    except Exception as e:
        return web.json_response({"ok": False, "error": str(e)}, status=500)
