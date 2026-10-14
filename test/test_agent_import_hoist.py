"""Module-scope ``efm_go.agent`` imports stay at module scope.

The four modules below import ``from efm_go.agent import ...`` at module
scope. ``efm_go.agent`` imports nothing from ``efm_go.dashboard.*`` or
``efm_go.session``, so no import cycle exists; these tests keep the imports
at module scope and prove no cycle exists in either load order.

Order-dependent cycles only surface in a fresh interpreter, not under a
bare import in an already-warm test process — hence the subprocess runs.
"""

import re
import subprocess
import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent.parent / "src"

_HOISTED_MODULES = (
    "efm_go.dashboard.handlers.agents",
    "efm_go.dashboard.handlers.mcp",
    "efm_go.dashboard.handlers.hooks",
    "efm_go.session",
)

_HOISTED_FILES = (
    "efm_go/dashboard/handlers/agents.py",
    "efm_go/dashboard/handlers/mcp.py",
    "efm_go/dashboard/handlers/hooks.py",
    "efm_go/session.py",
)


#: ``handlers/agents.py`` runs the functions its ``dashboard/agent_admin`` owners
#: define on its own globals, so the ratchet reads those owners as part of it.
_COMPOSED_OWNERS = {
    "efm_go/dashboard/handlers/agents.py": "efm_go/dashboard/agent_admin",
}


def _hoisted_text(rel: str) -> str:
    """*rel*'s source, followed by the owner modules it composes."""
    text = (_SRC / rel).read_text(encoding="utf-8")
    owner_dir = _COMPOSED_OWNERS.get(rel)
    if owner_dir is None:
        return text
    owners = sorted((_SRC / owner_dir).glob("[!_]*.py"))
    assert len(owners) >= 13, f"{owner_dir}: the composed owners were not found"
    return "\n".join([text, *(owner.read_text(encoding="utf-8") for owner in owners)])


def _fresh_import(statements: str) -> None:
    """Run import statements in a fresh child interpreter; fail on any error."""
    res = subprocess.run(
        [sys.executable, "-c", statements],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert res.returncode == 0, (
        f"fresh-interpreter import failed (a hoisted import created a cycle?):\n" f"{res.stderr}"
    )


def test_hoisted_modules_import_together_fresh() -> None:
    """All four hoisted modules import together in a cold interpreter."""
    _fresh_import("; ".join(f"import {m}" for m in _HOISTED_MODULES))


def test_hoisted_modules_import_agent_first_fresh() -> None:
    """Loading efm_go.agent BEFORE the handlers must also be cycle-free.

    A cycle between ``agent`` and these modules would be order-dependent:
    it can pass in one load order and raise ImportError in the other.
    """
    _fresh_import("; ".join(["import efm_go.agent"] + [f"import {m}" for m in _HOISTED_MODULES]))


def test_no_function_local_agent_imports_remain() -> None:
    """Ratchet: no function-local ``from efm_go.agent import`` in the four files.

    A reintroduced local import would silently undo the hoist and eventually
    re-grow the false ``# circular import`` folklore this fixed.  All three
    repo spellings are covered: ``from efm_go.agent import X``,
    ``import efm_go.agent``, and ``from efm_go import agent`` (the
    last matched on the bare ``agent`` name so sibling imports like
    ``agent_state`` don't trip it; comments are excluded from the match).
    """
    local_import = re.compile(
        r"^[ \t]+(?:"
        r"from efm_go\.agent import"
        r"|import efm_go\.agent\b"
        r"|from efm_go import [^#\n]*\bagent\b"
        r")",
        re.MULTILINE,
    )
    offenders = {}
    for rel in _HOISTED_FILES:
        text = _hoisted_text(rel)
        hits = local_import.findall(text)
        if hits:
            offenders[rel] = len(hits)
    assert not offenders, (
        f"function-local efm_go.agent imports reintroduced: {offenders}; "
        f"import at module scope instead (no cycle exists — see issue #1050)"
    )


def test_members_and_artifacts_import_first_fresh() -> None:
    """``efm_go.members`` (and so ``memory_stores.provision_member_memory``)
    must load in a process whose FIRST ``efm_go`` import reaches ``artifacts``.

    ``artifacts`` imports ``hooks`` at module scope, and ``hooks`` ->
    ``webhooks`` -> ``validation``; when ``validation`` read its content cap
    from ``artifacts`` that edge closed a cycle which raised ImportError in
    exactly this load order (the gateway and CLI dodged it only by importing
    ``validation`` first). The cap now lives in the ``constants`` leaf.
    """
    _fresh_import("import efm_go.members; import efm_go.artifacts")
    _fresh_import("import efm_go.artifacts; import efm_go.members")


def test_validation_is_a_leaf_that_never_imports_artifacts() -> None:
    """The closing edge stays deleted: loading ``validation`` must not pull
    ``artifacts`` in, or the cycle above is one hoisted import from returning."""
    _fresh_import(
        "import sys; import efm_go.validation; "
        "assert 'efm_go.artifacts' not in sys.modules, 'validation imports artifacts'"
    )
