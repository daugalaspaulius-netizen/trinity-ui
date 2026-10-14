"""Regression tests for the process-wide ``shutdown_event``.

The ``shutdown_event`` must not be a plain ``asyncio.Event()`` created at
module import time.  On Python 3.9 ``asyncio.Event`` captures the current loop
at construction; awaiting it later from a different loop (e.g. the one
``asyncio.run()`` creates for the gateway) raised::

    RuntimeError: Task <...> got Future <...> attached to a different loop

This crashed the gateway immediately after Slack connection and caused the
systemd service to restart every ~10s indefinitely.  These tests pin the
lazy-proxy behaviour so the regression cannot come back unnoticed.
"""

from __future__ import annotations

import asyncio

import efm_go


def test_shutdown_event_importable_without_running_loop() -> None:
    """Importing the module must not require a running event loop."""
    assert hasattr(efm_go, "shutdown_event")
    assert callable(efm_go.shutdown_event.set)
    assert callable(efm_go.shutdown_event.clear)
    assert callable(efm_go.shutdown_event.is_set)


def test_shutdown_event_survives_fresh_asyncio_run() -> None:
    """``await shutdown_event.wait()`` must work inside a fresh ``asyncio.run()``.

    This mirrors the exact pattern that crashed the gateway: the module is
    imported at top level, then ``asyncio.run()`` creates a new loop and the
    gateway coroutine awaits ``shutdown_event.wait()``.
    """
    efm_go.shutdown_event.clear()

    async def main() -> None:
        async def setter() -> None:
            await asyncio.sleep(0.01)
            efm_go.shutdown_event.set()

        asyncio.create_task(setter())
        await efm_go.shutdown_event.wait()

    asyncio.run(main())
    assert efm_go.shutdown_event.is_set()
    efm_go.shutdown_event.clear()


def test_shutdown_event_survives_multiple_asyncio_runs() -> None:
    """The proxy must rebind cleanly across successive loops."""
    for _ in range(3):

        async def main() -> None:
            async def setter() -> None:
                await asyncio.sleep(0.01)
                efm_go.shutdown_event.set()

            asyncio.create_task(setter())
            await efm_go.shutdown_event.wait()

        efm_go.shutdown_event.clear()
        asyncio.run(main())
        assert efm_go.shutdown_event.is_set()

    efm_go.shutdown_event.clear()


def test_shutdown_event_wait_for_timeout() -> None:
    """``asyncio.wait_for(shutdown_event.wait(), timeout=...)`` must work."""
    efm_go.shutdown_event.clear()

    async def main() -> str:
        try:
            await asyncio.wait_for(efm_go.shutdown_event.wait(), timeout=0.05)
        except asyncio.TimeoutError:
            return "timed_out"
        return "set"

    result = asyncio.run(main())
    assert result == "timed_out"


def test_shutdown_event_does_not_bind_to_default_loop_via_get_event_loop() -> None:
    """The proxy must not bind to a loop until awaited.

    Proves the proxy does NOT bind to the default loop on first access.
    """
    # Step 1: make sure there's a default loop on the main thread
    try:
        default_loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        default_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(default_loop)
    assert default_loop is not None

    # Step 2: reset the proxy's cached Event so it has to rebuild
    efm_go.shutdown_event.clear()
    efm_go.shutdown_event._event = None  # type: ignore[attr-defined]
    efm_go.shutdown_event._loop = None  # type: ignore[attr-defined]

    # Step 3 + 4: fresh loop via asyncio.run, must not cross-loop
    async def main() -> None:
        async def setter() -> None:
            await asyncio.sleep(0.01)
            efm_go.shutdown_event.set()

        asyncio.create_task(setter())
        await efm_go.shutdown_event.wait()

    asyncio.run(main())
    assert efm_go.shutdown_event.is_set()
    efm_go.shutdown_event.clear()


def test_shutdown_event_pending_set_preserved_across_loops() -> None:
    """A ``set()`` call without a running loop must survive until one starts."""
    # Reset
    efm_go.shutdown_event.clear()
    efm_go.shutdown_event._event = None  # type: ignore[attr-defined]
    efm_go.shutdown_event._loop = None  # type: ignore[attr-defined]

    # Sync set() before any loop runs
    efm_go.shutdown_event.set()
    assert efm_go.shutdown_event.is_set()

    async def main() -> bool:
        return efm_go.shutdown_event.is_set()

    assert asyncio.run(main()) is True
    efm_go.shutdown_event.clear()


def test_shutdown_event_get_raises_without_loop() -> None:
    """``_get()`` must raise RuntimeError when no loop is running."""
    efm_go.shutdown_event._event = None  # type: ignore[attr-defined]
    efm_go.shutdown_event._loop = None  # type: ignore[attr-defined]
    try:
        efm_go.shutdown_event._get()  # type: ignore[attr-defined]
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert "without a running event loop" in str(e)
    finally:
        efm_go.shutdown_event.clear()
