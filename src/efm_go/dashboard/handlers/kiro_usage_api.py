"""Direct RTS ``GetUsageLimits`` client for real Kiro credit usage.

Background — why this module exists
-----------------------------------
kiro-cli's ``/usage`` stdout stopped emitting the overage/total for org-managed
KIRO POWER accounts (it now caps at ``10000 of 10000 covered in plan``). The
dashboard credit pill scraped that text, so it froze at the plan limit even
when the account was well into overage. The real numbers still exist — the Kiro
IDE credit meter reads them from the ``GetUsageLimits`` API on the CodeWhisperer
runtime service (RTS). This module calls that same API so KiroCrew surfaces the
true used/limit/overage regardless of how kiro-cli reshuffles its stdout.

Whose credits are these?
------------------------
Several credentials can be readable at once (an IDE cache, a kiro-cli store, a
leftover file from a profile the user has since signed out of), and "unexpired"
does not mean "the one kiro-cli is actually using": a token for a signed-out
profile stays valid at the API until it expires on its own. Picking by fixed path
order therefore reports that profile's credits after a profile switch, and a
gateway restart does not help because the order is the same on boot.

So the caller passes ``expected_arn`` — the profile ARN ``kiro-cli whoami``
reports for itself — and a candidate is only used when its own
ListAvailableProfiles ARN equals it. Credentials for any other account are
skipped without being spent on a GetUsageLimits call. When every candidate is
rejected the function fails closed (``None``) and the caller degrades to
scraping kiro-cli's own ``/usage`` output, which describes the right account by
construction. Showing a different account's number is the failure being
prevented; showing no number for one refresh is not.

There are TWO proofs of ownership, never an unverified path. When whoami reports a
profile ARN, a candidate qualifies by matching it. When it reports none — a Builder
ID account, or an older kiro-cli that prints no ``Profile:`` block, or a whoami that
failed outright — a candidate qualifies only by PROVENANCE: it must come from
kiro-cli's own auth store, where a token is the signed-in account's credential by
construction. That is the same trust argument that makes scraping kiro-cli's own
``/usage`` output safe, so it costs nothing to rely on here.

What is refused in the no-ARN case is a credential from the JSON SSO caches or
another product's store. Those may well be the same account, but nothing proves it,
and treating them as interchangeable is what served one Builder ID account's
leftover token as a different Builder ID account's balance.

Provenance-anchoring is what keeps the API path available to every account class.
Requiring an ARN instead would push all profile-less accounts onto the text scrape —
a kiro-cli subprocess on every refresh, slower and lossier (recent kiro-cli prints
no overage line) than the direct call this module makes.

It is a read-only client: it reads the live bearer token that kiro-cli already
maintains and makes one authenticated call. The JSON SSO cache files live under
``~/.aws`` (a sensitive path), so they are read via
``hooks.safe_read_file_internal`` (which enforces ``is_sensitive_path`` and
emits a fail-closed SEL audit), not directly. On Linux, where those files are
not refreshed, the live token is read from the kiro-cli/amazon-q SQLite auth
store (``~/.local/share`` — not a sensitive path, so it cannot route through
``safe_read_file_internal``, but the credential read is still SEL-audited via
``hooks.emit_internal_read_audit`` and fails closed if the audit cannot be
recorded — opened read-only). It does NOT self-refresh the token via SSO-OIDC
(kiro-cli keeps the SQLite token fresh during normal use) — on 401/403 it fails
closed and the caller falls back to the legacy text scrape.

That freshness dependency is an OPERATIONAL requirement, not just an
implementation note. The store this module reads is refreshed as a side effect of
kiro-cli being driven, so on an install where the sign-in is owned elsewhere and
kiro-cli is never invoked directly, the stored token passes its expiry with
nothing to renew it. ``_unexpired`` then drops it, no credential is left to try,
and this module fails closed forever. Not refreshing here stays deliberate -- a
refresh belongs to whoever owns the sign-in -- but the caller must be able to
tell that state apart from "this account has no credit plan", because the two
have different remedies and only one of them is free. That is what the
``auth_state`` of :func:`fetch_usage_limits` reports, and it is why
:data:`AUTH_NO_CREDENTIAL` exists.

The HTTP call uses the Python standard library (``urllib``) rather than a
third-party client, so this module adds no new dependency to the public repo.

Security controls (fixed as acceptance criteria):
  1. Endpoint is a hardcoded AWS prod host from a region table keyed by the
     whoami profile ARN — never config-derived.
  2. TLS verification is always on (default ``ssl`` context: cert chain +
     hostname).
  3. Redirects are disabled (see ``_NoRedirect``) so the token can never be
     replayed to a redirected host.
  4. The bearer token is never logged (only HTTP status codes are).
  5. Any failure returns ``None`` (fail-closed) so the caller degrades to the
     text scrape rather than showing a fabricated number.
  6. The caller runs the returned dict through ``_redact_strings`` before it is
     cached and served.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import sqlite3
import ssl
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

from efm_go import hooks
from efm_go.identity_stores import Trust, sqlite_dbs

logger = logging.getLogger(__name__)

# Vendor credit hosts are gone. The remainder is the supplier prepaid balance.
_RTS_ENDPOINTS: dict[str, str] = {}
_DEFAULT_RTS_REGION = ""
_RTS_ENDPOINT = ""
_SVC = "com.amazon.aws.codewhisperer.runtime.AmazonCodeWhispererService"
_TARGET_GET_USAGE = f"{_SVC}.GetUsageLimits"
_TARGET_LIST_PROFILES = f"{_SVC}.ListAvailableProfiles"
_CONTENT_TYPE = "application/x-amz-json-1.0"
# A Kiro/Q user-agent is required for the IDE-origin code path; without it the
# API rejects the request.
_USER_AGENT = "AmazonQ-For-CLI/1.24.0 ua/2.0 os/linux lang/rust KiroCrew"
_TIMEOUT_SECS = 15
# Aggregate wall-clock budget across ALL candidate tokens. Each token can cost
# up to two 15s requests (ListAvailableProfiles + GetUsageLimits), and there can
# be several candidates, so without this the pill could spin for minutes before
# falling back to the text scrape. Once exceeded we stop trying tokens and let
# the caller degrade to the scrape.
_TOTAL_DEADLINE_SECS = 30

# ``auth_state`` values reported by :func:`fetch_usage_limits`, so the
# caller can tell an AUTH-CLASS failure (one a fresh sign-in fixes) from every
# other reason the usage read came back empty.
#
# The distinction is not cosmetic. The ``/usage`` text scrape that follows a failed
# read is a kiro-cli slash command over this same API, so it needs the same sign-in
# and fails the same way when the stored credential has expired. Reporting that as
# "the account has no credit plan" names a cause that did not happen; the one remedy
# is a fresh sign-in, and the pill can only say so when the failure is known to be
# auth-class. Only these two states may be reported as "sign in again"; everything
# else stays deliberately unclassified.

#: A candidate credential was accepted and usage was returned.
AUTH_OK = "ok"
#: No unexpired credential was readable at all, so no request was even attempted.
#: This is the expired-store state: ``_unexpired`` drops a lapsed token, leaving
#: nothing to try. It also covers "never signed in" and "the credential could not
#: be read", which are deliberately NOT split out -- the remedy is the same for
#: all three, and none of them can be told apart without claiming more than is
#: known.
AUTH_NO_CREDENTIAL = "no_credential"
#: A credential was tried against GetUsageLimits and answered 401, i.e. it is no
#: longer honoured (revoked or rotated out from under us).
#:
#: 401 ONLY. A 403 is authenticated-but-not-permitted -- an entitlement problem,
#: where "sign in again" would be wrong advice -- so it stays :data:`AUTH_OTHER`,
#: as does a 401 that ListAvailableProfiles absorbs (``_list_profile_arn``
#: reports any non-200 as None, so that case presents as an unproven candidate
#: and is not observable here). Narrow on purpose: telling a user with a working
#: sign-in to re-authenticate is its own defect.
AUTH_REJECTED = "rejected"
#: Not an auth problem, or not provably one: no CREDIT breakdown for the account,
#: an unproven candidate, a transport error, a 403, an unparseable body.
AUTH_OTHER = "other"

# Live bearer token sources kiro-cli / the Kiro IDE maintain.
#
# The JSON SSO cache files live under ``~/.aws`` (a sensitive credential path),
# so they are NOT read directly here — they are read via
# ``hooks.safe_read_file_internal(read_id)``, which enforces ``is_sensitive_path``
# and emits a fail-closed SEL audit. The read-ids below are registered in
# ``efm_go.hooks._INTERNAL_READ_ALLOWLIST``.
_JSON_TOKEN_READ_IDS = (
    "kiro_usage_api.sso_token_cli",
    "kiro_usage_api.sso_token_ide",
)

# kiro-cli's OWN SQLite auth store — the store kiro-cli itself authenticates
# from, and the authoritative live-token source (it refreshes this during normal
# use; the JSON files above are not rewritten on refresh). Being kiro-cli's own
# store is what makes a token here provably the SIGNED-IN account's credential,
# which is the basis of the source-anchored path in ``fetch_usage_limits`` — the
# same trust argument as scraping kiro-cli's own ``/usage`` output. On this host
# the running ``kiro-cli acp`` processes were observed holding descriptors on
# exactly this path.
# ``~/.local/share`` is not a sensitive credential path, so this read is a direct
# read-only sqlite open. auth_kv holds a JSON blob per key.
#
# The entries are deliberately UNGUARDED by ``sys.platform``: every candidate is
# existence-checked before it is opened, so a path that cannot exist on the
# running OS is inert, and a platform-independent module constant is what lets
# tests patch the tuple without becoming host-dependent.
#
# The Windows entries are the fixed default locations, NOT resolved from
# ``%LOCALAPPDATA%`` / ``%APPDATA%``. Membership here is a trust claim
# (``from_cli_store=True``) that rests on agent file tools being unable to
# write the store, and that fence (``_SENSITIVE_HOME_DIRS``) is home-anchored
# at exactly these paths -- so an env-resolved location either equals an entry
# or falls outside the fence and must not be trusted. A redirected profile
# therefore keeps the text-scrape fallback rather than gaining a forgeable
# trusted path; the same posture as the Linux entry, which does not follow
# ``XDG_DATA_HOME`` redirection either.
#
# ``AppData/Local`` is where current kiro-cli actually writes on Windows (its
# data dir resolves to the local, non-roaming app-data directory -- the same
# resolver family that yields ``~/.local/share`` on Linux and
# ``~/Library/Application Support`` on macOS, both matching the entries
# above). ``AppData/Roaming`` is retained for layouts that used the roaming
# location; a path that does not exist on the running host is inert.
_CLI_SQLITE_DBS = sqlite_dbs(Trust.TRUSTED)

# Auth stores belonging to OTHER products (amazon-q). Readable, and often the same
# account, but NOT kiro-cli's own credential — so a token from here can only be
# used when a matching profile ARN proves the account independently. It can never
# satisfy the source-anchored path.
#
# The Windows entries mirror the kiro-cli tuple above rather than stopping at the
# POSIX layouts: the fence (``_SENSITIVE_HOME_DIRS``) and sign-in staging both
# already name ``AppData/{Local,Roaming}/amazon-q``, so omitting them here made
# an amazon-q token unreadable for usage on exactly the platform where it is
# fenced -- a store every writer treats as a secret and this reader treats as
# absent. Untrusted either way (``from_cli_store=False``), so this widens what
# can be READ for credit reporting, never what is believed.
_OTHER_SQLITE_DBS = sqlite_dbs(Trust.OTHER)
_SQLITE_TOKEN_KEYS = ("kirocli:odic:token", "codewhisperer:odic:token", "kirocli:social:token", "kirocli:external-idp:token")

# SEL audit label for the SQLite live-token read. Not an allowlist entry (that
# gate is for sensitive-path reads via safe_read_file_internal); this is only
# the audit event's tool_name so the credential access is traceable.
_SQLITE_AUDIT_READ_ID = "kiro_usage_api.sqlite_token"

# Range guard: reject absurd numbers so a corrupt/hostile response can't render
# as a wild figure. Real plans are in the thousands; a million-credit ceiling is
# comfortably above any real plan while still catching garbage.
_MAX_CREDITS = 1_000_000.0
_MAX_BONUS_GRANTS = 32
_MAX_BONUS_NAME_CHARS = 100

# Cap the RTS response body so an oversized or indefinitely-streamed response
# cannot exhaust memory or tie up a shared subprocess worker. The usage JSON is
# a few KB; 1 MB is comfortably above any real response.
_MAX_RESP_BYTES = 1_000_000

# Memoized account profile ARN (stable per account). Keyed by
# (token digest, expected-ARN digest) -- see _profile_cache_key -- so two probes
# with the same token but different expected ARNs never serve each other's
# answer. Populated only from a definitive ListAvailableProfiles 200 that
# yielded an ARN; transient failures, empty lists, and anchored misses are
# never cached. See _list_profile_arn.
_PROFILE_ARN_CACHE: dict[str, str | None] = {}

# Size cap for the two profile caches below. They are keyed by token digest and
# never expire, so a long-lived gateway that sees many profile switches / token
# refreshes would otherwise accumulate one entry each. See _remember_profile.
_PROFILE_CACHE_MAX = 32

# Human profile/display name for the signed-in account, captured as a side
# effect of the same ListAvailableProfiles probe that yields the ARN and keyed
# by the same token digest. Surfaced as the usage dict's ``account`` field so
# the dashboard can show WHO the plan belongs to. Populated only alongside a
# found ARN (control-flow-coupled to _PROFILE_ARN_CACHE); may be None when the
# profile carries no name.
_PROFILE_NAME_CACHE: dict[str, str | None] = {}

# One WARN per api->text degradation transition (reset on the next success) so
# a persistently-failing API path is diagnosable at the default log level
# without spamming, and the legitimate no-token case stays at DEBUG.
_API_DEGRADED_WARNED = False


class _RequestError(Exception):
    """Transport-level failure (DNS, connect, TLS, timeout) from :func:`_post`.

    This is the analog of ``requests.exceptions.RequestException``. A non-2xx
    HTTP *response* is NOT a ``_RequestError``: it is returned as a ``_Resp`` so
    the caller can branch on ``status_code`` (mirroring requests, which does not
    raise on 4xx/5xx)."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Disable HTTP redirects (security control 3).

    Returning ``None`` makes urllib raise the 3xx as an ``HTTPError`` rather
    than following it, so the bearer token is never replayed to a redirected
    host."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


class _Resp:
    """Minimal response view exposing only what the call sites use
    (``status_code`` and ``json()``), so the urllib transport is a drop-in for
    the previous requests-based one and the call sites stay unchanged."""

    __slots__ = ("status_code", "_text")

    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self._text = text

    def json(self) -> dict:
        return json.loads(self._text) if self._text else {}


def _build_opener() -> urllib.request.OpenerDirector:
    """Build an opener with TLS verification ON (control 2) and redirects
    DISABLED (control 3).

    A fresh default SSL context verifies the certificate chain and hostname;
    ``_NoRedirect`` turns any 3xx into an error instead of replaying the bearer
    token to a redirected host."""
    ctx = ssl.create_default_context()  # verify_mode=CERT_REQUIRED, check_hostname=True
    return urllib.request.build_opener(
        _NoRedirect(),
        urllib.request.HTTPSHandler(context=ctx),
    )


def _note_api_outcome(ok: bool, reason: str = "") -> None:
    """Track API-path health: WARN once (with the terminal reason) when tokens
    existed but every candidate failed, reset on the next success."""
    global _API_DEGRADED_WARNED
    if ok:
        _API_DEGRADED_WARNED = False
        return
    if not _API_DEGRADED_WARNED:
        _API_DEGRADED_WARNED = True
        logger.warning(
            "Kiro usage API degraded to text-scrape fallback (%s) — "
            "overage will not be visible until the API path recovers",
            reason,
        )


def _parse_iso(ts: object) -> datetime | None:
    """Parse an ISO8601 timestamp (handles trailing Z) to an aware datetime.

    kiro-cli emits nanosecond precision (9 fractional digits); Python 3.10's
    ``fromisoformat`` accepts at most 6, so the fraction is truncated to
    microseconds first. Without this the parse fails and an expired token would
    be treated as non-expiring (fail-open).
    """
    try:
        s = str(ts).replace("Z", "+00:00")
        s = re.sub(r"(\.\d{6})\d+", r"\1", s)
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def _expiry_if_unexpired(exp: object, now: datetime) -> datetime | None:
    """Return the parsed expiry only when it is present, parseable, and future.

    Deny-by-default, same contract as :func:`_unexpired` (which delegates here):
    a missing or unparseable expiry rejects the credential rather than treating
    it as non-expiring. The parsed value is returned rather than a bool so
    :func:`_candidate_tokens` can order candidates by it without re-parsing.
    """
    if not exp:
        return None
    parsed = _parse_iso(exp)
    if parsed is None or parsed <= now:
        return None
    return parsed


def _unexpired(exp: object, now: datetime) -> bool:
    """True only when the expiry is present, parseable, and in the future.

    Deny-by-default: a missing or unparseable expiry rejects the token rather
    than treating it as non-expiring. Both real stores always carry an expiry
    field, and the multi-candidate loop + text-scrape fallback absorb a false
    rejection gracefully — failing closed here costs nothing.
    """
    return _expiry_if_unexpired(exp, now) is not None


def _token_from_json(read_id: str, now: datetime) -> tuple[str, datetime] | None:
    """Return ``(accessToken, expiry)`` from a sanctioned JSON SSO cache read.

    The bytes are read via ``hooks.safe_read_file_internal`` (not a direct
    ``~/.aws`` read) so the sensitive-path deny rule + SEL audit apply. The
    expiry is returned alongside the token so candidates can be ordered by
    freshness; ``None`` means no usable unexpired credential here.
    """
    raw = hooks.safe_read_file_internal(read_id)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    tok = data.get("accessToken") or data.get("access_token")
    exp = data.get("expiresAt") or data.get("expires_at")
    if not isinstance(tok, str) or not tok:
        return None
    expiry = _expiry_if_unexpired(exp, now)
    return (tok, expiry) if expiry is not None else None


def _token_from_sqlite(db: Path, now: datetime) -> tuple[str, datetime] | None:
    """Return ``(access_token, expiry)`` from a kiro-cli/amazon-q SQLite store.

    Opened read-only; the token value is never logged. This is the live token
    source on Linux, where the JSON cache file is not refreshed. The store is
    now classified sensitive (``is_sensitive_path``), so agent file tools cannot
    read it; this audited helper is the sole sanctioned reader. It cannot route
    through the byte-oriented ``hooks.safe_read_file_internal`` (sqlite needs to
    open the DB file), so the credential access is audited via
    ``hooks.emit_internal_read_audit`` (same SEL event + fail-closed carve-out
    as the JSON path): a successful read whose audit cannot be recorded is
    denied (returns None) rather than handing back an unaudited credential. A
    symlinked DB path is refused so the read cannot be redirected to another file.
    """
    try:
        if db.is_symlink() or not db.exists():
            return None
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except (sqlite3.Error, OSError):
        # OSError covers db.exists() on a permission-denied path — the
        # fail-closed contract must hold for it too.
        hooks.emit_internal_read_audit(_SQLITE_AUDIT_READ_ID, "unreadable")
        return None
    try:
        audited = False
        for key in _SQLITE_TOKEN_KEYS:
            try:
                row = con.execute(
                    "SELECT value FROM auth_kv WHERE key=?", (key,)
                ).fetchone()
            except sqlite3.Error:
                continue
            if not row:
                continue
            try:
                blob = json.loads(row[0])
            except (ValueError, TypeError):
                continue
            if not isinstance(blob, dict):
                continue
            tok = blob.get("access_token") or blob.get("accessToken")
            exp = blob.get("expires_at") or blob.get("expiresAt")
            if isinstance(tok, str) and tok:
                expiry = _expiry_if_unexpired(exp, now)
                if expiry is None:
                    # The credential blob WAS read even though it is expired —
                    # record that access so the audit trail covers every read
                    # of the store, not only reads that yield a usable token.
                    hooks.emit_internal_read_audit(_SQLITE_AUDIT_READ_ID, "expired")
                    audited = True
                    continue
                # Audit the live-token read; fail closed if it can't be recorded
                # (a logger line is not an SEL audit) so an unaudited credential
                # is never returned — the caller degrades to the text scrape.
                if not hooks.emit_internal_read_audit(_SQLITE_AUDIT_READ_ID, "success"):
                    return None
                return (tok, expiry)
        # Audit-on-every-outcome: the DB was opened, so record the access even
        # when it yielded no usable token (missing rows / malformed blob / query
        # failure) — otherwise an opened credential store would leave no trail.
        if not audited:
            hooks.emit_internal_read_audit(_SQLITE_AUDIT_READ_ID, "no_token")
        return None
    finally:
        con.close()


class _Candidate(NamedTuple):
    """A usable bearer token plus the provenance needed to trust it.

    ``from_cli_store`` is True only for a token read from kiro-cli's OWN auth
    store (:data:`_CLI_SQLITE_DBS`). That flag is a trust claim, not a label: it
    is what lets :func:`fetch_usage_limits` accept a credential for an account
    with no profile ARN, because a token in kiro-cli's own store is the
    signed-in account's credential by construction. Tokens from the JSON SSO
    caches and from other products' stores carry False — they may well be the
    same account, but nothing here proves it, so they are usable only when a
    matching ARN proves it independently.
    """

    token: str
    expiry: datetime
    from_cli_store: bool


def _candidate_tokens() -> list[_Candidate]:
    """Return all unexpired candidates to try, kiro-cli's own store first, then
    freshest expiry (deduped).

    Path order is deliberately NOT the ranking. Every enumerated source can hold
    a valid credential at the same time, so ordering by path meant a leftover
    token from a profile the user has since signed out of was tried first and,
    being genuinely valid, was accepted — the "wrong profile" readout. Ordering
    by expiry descending puts the most recently issued credential first, because
    a token refreshed later carries a later expiry.

    This is a heuristic, not proof: sources can issue different lifetimes, so a
    long-lived stale token could still outrank a short-lived fresh one. Ordering
    only decides which proven candidate is tried first —
    ``fetch_usage_limits`` establishes ownership itself, by matching ARN or by
    provenance. Ties keep the original path precedence (``sorted`` is stable).

    Provenance ranks above expiry. Two accounts entitled to one shared IdC
    profile report the same ARN, so the ARN proof cannot tell them apart and
    the first candidate to clear it wins. A token in kiro-cli's own store is
    the signed-in account's credential by construction, so it goes first; a
    fresher leftover in an SSO cache must not outrank it. Expiry breaks ties
    within each provenance class.

    Multiple candidates are returned (not just the first) because "unexpired" is
    not the same as "accepted": an unexpired-but-rejected token must not shadow a
    working one. Expired tokens are skipped and token values are never logged.
    v1 does not refresh — kiro-cli keeps its own store fresh during normal use.
    """
    now = datetime.now(timezone.utc)
    # Deduped by token value, keeping the latest expiry seen for it and ORing the
    # provenance: the same token can appear in more than one store, and if any of
    # them is kiro-cli's own store then it is kiro-cli's credential.
    freshest: dict[str, tuple[datetime, bool]] = {}

    def _add(found: tuple[str, datetime] | None, *, from_cli_store: bool) -> None:
        if not found:
            return
        tok, exp = found
        current = freshest.get(tok)
        if current is None:
            freshest[tok] = (exp, from_cli_store)
        else:
            freshest[tok] = (max(exp, current[0]), current[1] or from_cli_store)

    for read_id in _JSON_TOKEN_READ_IDS:
        _add(_token_from_json(read_id, now), from_cli_store=False)
    for db in _CLI_SQLITE_DBS:
        _add(_token_from_sqlite(db, now), from_cli_store=True)
    for db in _OTHER_SQLITE_DBS:
        _add(_token_from_sqlite(db, now), from_cli_store=False)
    # (from_cli_store, expiry) descending: own-store tokens first, freshest first.
    ranked = sorted(freshest.items(), key=lambda kv: (kv[1][1], kv[1][0]), reverse=True)
    return [_Candidate(tok, exp, own) for tok, (exp, own) in ranked]


def _load_bearer_token() -> str | None:
    """Return the first-ranked available bearer token, or None.

    Thin convenience wrapper over :func:`_candidate_tokens` (first candidate:
    kiro-cli's own store first, then freshest expiry). It discards provenance and applies NO
    ownership proof, so it must not be used to choose the credential a request is
    made with — ``fetch_usage_limits`` uses :func:`_candidate_tokens` directly so
    it can check each candidate's account (by ARN or by provenance) and fall
    through to the next source on a rejected-but-unexpired token.
    """
    candidates = _candidate_tokens()
    return candidates[0].token if candidates else None


def _region_from_arn(arn: str | None) -> str:
    """Return the CodeWhisperer region in ``arn``, or the commercial default.

    Profile ARNs are ``arn:aws:codewhisperer:<region>:<account>:profile/<name>``.
    A missing or malformed ARN, or a region not in :data:`_RTS_ENDPOINTS`,
    falls back to us-east-1 so the request still goes to a known AWS prod host.
    """
    if not isinstance(arn, str) or not arn:
        return _DEFAULT_RTS_REGION
    parts = arn.split(":")
    if len(parts) < 6 or parts[2] != "codewhisperer":
        return _DEFAULT_RTS_REGION
    region = parts[3]
    return region if region in _RTS_ENDPOINTS else _DEFAULT_RTS_REGION


def _rts_endpoint(arn: str | None = None) -> str:
    """Hardcoded RTS host for ``arn``'s region (control 1)."""
    return _RTS_ENDPOINTS[_region_from_arn(arn)]


def _post(token: str, target: str, payload: dict, *, endpoint: str | None = None) -> _Resp:
    """Vendor credit POST is disconnected."""
    raise _RequestError("EFM Go: vendor usage POST is disconnected")


def _read_capped(fp: object) -> str:
    """Read at most ``_MAX_RESP_BYTES`` from a response body.

    A bounded read so an oversized or indefinitely-streamed response cannot
    exhaust memory or tie up a shared subprocess worker. Returns ``""`` when the
    body exceeds the cap — which parses to an empty dict and fails closed to the
    text scrape.
    """
    data = fp.read(_MAX_RESP_BYTES + 1)  # type: ignore[attr-defined]
    if len(data) > _MAX_RESP_BYTES:
        logger.debug("Kiro usage API: response body exceeded %d bytes; discarded", _MAX_RESP_BYTES)
        return ""
    return data.decode("utf-8", "replace")


def _profile_cache_key(token: str, expected_arn: str | None) -> str:
    """Cache key for the profile caches: token digest + expected-ARN digest.

    Keyed by BOTH so two probes with the same token but different expected
    ARNs can never serve each other's answer — one memoized ARN per token
    digest is what made a wrong first selection sticky for the process
    lifetime. Never the raw token (control 5); the ARN is digested too so the
    key shape stays uniform. A falsy anchor ("" or None) means "no question
    asked" and maps to one shared key.
    """
    tok = hashlib.sha256(token.encode()).hexdigest()[:16]
    anchor = hashlib.sha256((expected_arn or "").encode()).hexdigest()[:16]
    return f"{tok}:{anchor}"


def _list_profile_arn(
    token: str, *, expected_arn: str | None = None, endpoint: str | None = None
) -> str | None:
    """Return the profile ARN this token should use, or None.

    Enterprise/IdC accounts (KIRO POWER etc.) must pass ``profileArn`` to
    GetUsageLimits or it returns 403 FEATURE_NOT_SUPPORTED.

    ``expected_arn`` is the question being asked: when supplied, the answer
    is that ARN if it is present in THIS token's own ListAvailableProfiles
    list, else None. Presence in the token's own list is what proves the
    credential belongs to the signed-in account — position proves nothing,
    because a token entitled to several profiles returns them in an order the
    caller does not control. When no anchor is supplied (source-anchored
    mode) the first entry carrying an ARN is the answer.

    The answer is account-stable per (token, question), so a found ARN is
    memoized in ``_PROFILE_ARN_CACHE`` keyed by :func:`_profile_cache_key`
    (never the token itself) to save one RTS round-trip per refresh. Three
    things are deliberately NOT cached: transient failures (network error,
    non-200), a 200 with no profiles, and an anchored miss (expected ARN
    absent from the list) — an empty or incomplete list can be post-login
    propagation lag on an enterprise account, so pinning the miss would
    strand that account on the text fallback until restart. All are re-probed
    on the next refresh, and each candidate token is probed for its own
    account (no cross-token reuse).
    """
    key = _profile_cache_key(token, expected_arn)
    if key in _PROFILE_ARN_CACHE:
        return _PROFILE_ARN_CACHE[key]
    try:
        r = _post(token, _TARGET_LIST_PROFILES, {}, endpoint=endpoint)
    except _RequestError:
        return None
    if r.status_code != 200:
        return None
    try:
        body = r.json()
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None
    profiles = body.get("profiles")
    if not isinstance(profiles, list):
        return None
    arn: str | None = None
    name: str | None = None
    for p in profiles:
        if not isinstance(p, dict):
            continue
        candidate = p.get("arn") or p.get("profileArn")
        if not candidate:
            continue
        if expected_arn and candidate != expected_arn:
            # Anchored mode: only the asked-about profile is an answer.
            continue
        arn = candidate
        # Human label for the signed-in account. Bounded like the plan name
        # so a hostile/oversized value can't reach the cache/UI unbounded;
        # only a non-empty string qualifies.
        pname = p.get("profileName") or p.get("profileDisplayName")
        if isinstance(pname, str) and pname:
            name = pname[:100]
        break
    if arn is not None:
        _remember_profile(key, arn, name)
    return arn


def _remember_profile(key: str, arn: str, name: str | None) -> None:
    """Memoize a found ARN (and its co-cached display name) under a size cap.

    Entries are keyed by token digest and never expire, so each profile switch
    or token refresh adds one. The cap bounds that growth over a long-lived
    gateway; eviction is insertion-order (dicts preserve it), and both caches are
    evicted together so a name can never outlive the ARN it belongs to and be
    attributed to a different account.
    """
    if key not in _PROFILE_ARN_CACHE and len(_PROFILE_ARN_CACHE) >= _PROFILE_CACHE_MAX:
        oldest = next(iter(_PROFILE_ARN_CACHE), None)
        if oldest is not None:
            _PROFILE_ARN_CACHE.pop(oldest, None)
            _PROFILE_NAME_CACHE.pop(oldest, None)
    _PROFILE_ARN_CACHE[key] = arn
    _PROFILE_NAME_CACHE[key] = name


def _account_name(token: str, expected_arn: str | None = None) -> str | None:
    """Return the cached profile display name for ``token``, or None.

    Populated as a side effect of :func:`_list_profile_arn`; this getter never
    issues a request itself, so the ARN probe must have run first (it always
    does in ``fetch_usage_limits``), and ``expected_arn`` must be the same
    anchor that probe was asked about. Keyed by :func:`_profile_cache_key`
    (never the token itself)."""
    return _PROFILE_NAME_CACHE.get(_profile_cache_key(token, expected_arn))


def _bounded(value: object) -> float | None:
    """Coerce to a finite float within the safe range, else None."""
    try:
        f = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f) or f < 0 or f > _MAX_CREDITS:
        return None
    return f


def _map_response(data: dict) -> dict | None:
    """Translate a GetUsageLimits response into KiroCrew's canonical usage dict.

    Canonical shape (shared with the text-scrape fallback so consumers never
    branch on source):
      credits_used     total consumed this cycle (currentUsage)
      credits_plan     plan limit (usageLimit)
      credits_overage  overage above plan (currentOverages, else max(0, used-plan))
      credits_covered  in-plan portion = min(used, plan)
      percentage       used / plan * 100 (source-authoritative; may exceed 100)
      cost_usd         overage charges
      overage_rate     per-credit overage rate
      plan, resets     display strings
      source           "api"

    Returns None when no usable CREDIT breakdown with a finite used+limit exists.
    """
    if not isinstance(data, dict):
        return None
    breakdowns = data.get("usageBreakdownList")
    if not isinstance(breakdowns, list):
        breakdowns = []
    # Drop any non-dict entries so a malformed shape (e.g. [null]) can't raise
    # AttributeError and strand the caller on {"available": False} instead of
    # the text fallback.
    breakdowns = [b for b in breakdowns if isinstance(b, dict)]
    credit = None
    for b in breakdowns:
        if b.get("resourceType") == "CREDIT":
            credit = b
            break
    if credit is None:
        # Legacy/untyped responses omit resourceType — accept a single untyped
        # entry, but never a typed non-CREDIT entry (e.g. a TOKEN quota), which
        # would display an unrelated number as the credit total.
        for b in breakdowns:
            if not b.get("resourceType"):
                credit = b
                break
    if not credit:
        return None

    # Ambiguity probe (observation only — selection above is unchanged). The
    # plan-pool picker takes the FIRST entry that is exactly resourceType
    # "CREDIT", so a second CREDIT-typed pool (e.g. a promotional/welcome grant
    # typed literally "CREDIT" rather than a bonus marker) can win the plan slot
    # by list order and displace the real plan pool — a latent, unobserved case
    # with no captured payload. When more than one entry satisfies the plan-pool
    # test we record the SHAPE so a maintainer can choose a remedy (fail-closed
    # vs deterministic pick) against real evidence. Log resource types and
    # counts only, never balances or identifiers (billing-adjacent). Additive:
    # nothing about which pool wins changes.
    _credit_typed = [b for b in breakdowns if b.get("resourceType") == "CREDIT"]
    if len(_credit_typed) > 1:
        logger.warning(
            "Kiro usage API: %d CREDIT-typed pools in usageBreakdownList "
            "(resource types %s); plan pool selected by list order at index %d "
            "— a second CREDIT-typed pool may be displacing the real plan pool",
            len(_credit_typed),
            [str(b.get("resourceType")) for b in breakdowns],
            breakdowns.index(credit),
        )

    # Prefer the *-WithPrecision fields only when they are valid numbers; a
    # present-but-null/malformed precision value must fall back to the legacy
    # currentUsage/usageLimit rather than reject an otherwise-valid response.
    used = _bounded(credit.get("currentUsageWithPrecision"))
    if used is None:
        used = _bounded(credit.get("currentUsage"))
    plan = _bounded(credit.get("usageLimitWithPrecision"))
    if plan is None:
        plan = _bounded(credit.get("usageLimit"))
    if used is None or plan is None or plan <= 0:
        return None

    overage = _bounded(credit.get("currentOverages"))
    if overage is None:
        overage = max(0.0, used - plan)

    result: dict[str, object] = {
        "credits_used": used,
        "credits_plan": plan,
        "credits_overage": overage,
        "credits_covered": min(used, plan),
        "percentage": round(used / plan * 100, 1),
        "source": "api",
    }

    rate = _bounded(credit.get("overageRate"))
    if rate is not None:
        result["overage_rate"] = rate
    cost = _bounded(credit.get("overageCharges"))
    if cost is not None:
        result["cost_usd"] = cost

    sub = data.get("subscriptionInfo")
    if not isinstance(sub, dict):
        sub = {}
    plan_name = sub.get("subscriptionTitle") or sub.get("type")
    # Only a non-empty string may reach the dashboard as usage.plan — an object
    # or array here would be cached and handed to React, crashing the usage UI.
    # Bound the length defensively too.
    if isinstance(plan_name, str) and plan_name:
        result["plan"] = plan_name[:100]

    ts = data.get("nextDateReset")
    if ts is not None:
        try:
            result["resets"] = datetime.fromtimestamp(
                float(ts), tz=timezone.utc
            ).strftime("%Y-%m-%d")
        except (ValueError, OSError, OverflowError, TypeError):
            pass

    # Best-effort bonus / free-trial pools. GetUsageLimits can carry additional
    # breakdown entries (promotional / welcome or free-trial pools) that are spent
    # BEFORE the plan; kiro-cli's text output shows the same thing as a "Bonus
    # Credits" section. The exact resourceType label is not documented, so match
    # conservatively on known bonus-like markers and never treat the primary
    # CREDIT entry or an unrelated quota (e.g. TOKEN) as bonus. Emitted only when
    # a finite used+limit pair exists, mirroring the text-scrape fields so the
    # dashboard never branches on source. Retain every bounded grant; the legacy
    # scalar fields mirror the first one for older clients.
    _bonus_markers = ("FREE_TRIAL", "FREETRIAL", "TRIAL", "BONUS", "PROMO", "GIFT", "WELCOME")
    bonus_credits: list[dict[str, object]] = []
    for b in breakdowns:
        if b is credit:
            continue
        rtype = str(b.get("resourceType") or "").upper()
        if not any(mk in rtype for mk in _bonus_markers):
            continue
        b_used = _bounded(b.get("currentUsageWithPrecision"))
        if b_used is None:
            b_used = _bounded(b.get("currentUsage"))
        b_limit = _bounded(b.get("usageLimitWithPrecision"))
        if b_limit is None:
            b_limit = _bounded(b.get("usageLimit"))
        if b_used is None or b_limit is None or b_limit <= 0:
            continue
        label = b.get("title") or b.get("displayName") or rtype.replace("_", " ").title()
        if not isinstance(label, str) or not label or not label.isprintable():
            continue
        bonus_credits.append(
            {
                "name": label[:_MAX_BONUS_NAME_CHARS],
                "used": b_used,
                "total": b_limit,
            }
        )
        if len(bonus_credits) >= _MAX_BONUS_GRANTS:
            break
    if bonus_credits:
        result["bonus_credits"] = bonus_credits
        first = bonus_credits[0]
        result["bonus_used"] = first["used"]
        result["bonus_limit"] = first["total"]
        result["bonus_label"] = first["name"]

    return result


class UsageResult(NamedTuple):
    """A usage read plus WHY it came back empty, when it did.

    ``usage`` keeps the historical meaning exactly: the canonical usage dict on
    success, ``None`` on any failure. ``auth_state`` is the added signal, and it
    carries no credential material -- it is one of the four ``AUTH_*`` constants
    and nothing else, so a token value can never ride out of this module on it
    (control 4).

    The two travel together in ONE return value rather than the module offering a
    second dict-only entry point, because a second entry point nothing calls is
    dead API, and every test patches this function by name: widening the return
    type makes a stale patch fail loudly, where a second name beside it lets such a
    patch keep intercepting a function the caller does not call and pass vacuously
    while the real credential stores are read.
    """

    usage: dict | None
    auth_state: str



def _get_supplier_json(url: str, key: str) -> dict | None:
    """GET a supplier balance. The key is a header only and is never logged."""
    req = urllib.request.Request(
        url,
        method="GET",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            raw = resp.read(65536)
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    try:
        data = json.loads(raw.decode("utf-8", "replace"))
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _supplier_usage() -> UsageResult:
    """Prepaid remainder from OpenRouter and SiliconFlow. No vendor credit POST."""
    used = 0.0
    plan = 0.0
    names: list[str] = []
    saw_key = False
    or_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if or_key:
        saw_key = True
        body = _get_supplier_json("https://openrouter.ai/api/v1/credits", or_key)
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict):
            total = _bounded(data.get("total_credits"))
            spent = _bounded(data.get("total_usage"))
            if total is not None:
                names.append("OpenRouter")
                plan += total
                used += spent or 0.0
    sf_key = os.environ.get("SILICONFLOW_API_KEY", "").strip()
    if sf_key:
        saw_key = True
        body = _get_supplier_json("https://api.siliconflow.cn/v1/user/info", sf_key)
        data = body.get("data") if isinstance(body, dict) else None
        if isinstance(data, dict):
            remaining = _bounded(data.get("balance"))
            if remaining is None:
                remaining = _bounded(data.get("totalBalance"))
            if remaining is not None:
                names.append("SiliconFlow")
                plan += remaining
    if not names:
        return UsageResult(None, AUTH_NO_CREDENTIAL if not saw_key else AUTH_OTHER)
    return UsageResult(
        {
            "credits_used": used,
            "credits_plan": plan,
            "credits_overage": max(0.0, used - plan),
            "credits_covered": min(used, plan),
            "percentage": (used / plan * 100.0) if plan else 0.0,
            "plan": "+".join(names),
            "source": "supplier",
        },
        AUTH_OK,
    )


def fetch_usage_limits(expected_arn: str | None) -> UsageResult:
    """Fetch real credit usage via the direct RTS API. Synchronous (uses urllib).

    A candidate credential is used only when its ownership by the signed-in
    account is PROVEN. There are two proofs, and ``expected_arn`` selects which:

    * **ARN-anchored** (``expected_arn`` is a non-empty ARN — the one
      ``kiro-cli whoami`` reports for itself): a candidate qualifies when its own
      ListAvailableProfiles ARN is present and equal. This admits a credential
      from any readable source, including an IDE cache, because the ARN match is
      the proof.
    * **Source-anchored** (``expected_arn`` is ``None`` — the account has no
      profile ARN, or whoami could not be resolved): a candidate qualifies only if
      it came from kiro-cli's OWN auth store (``from_cli_store``). A token there is
      the signed-in account's credential by construction — the identical trust
      argument that makes scraping kiro-cli's own ``/usage`` output safe. Whatever
      ARN that credential reports is then used for the request payload, so an
      enterprise account on a kiro-cli that prints no ``Profile:`` block still gets
      its real overage figure instead of the lossier scrape.

    ``None`` is therefore NOT an unverified mode: it swaps ARN proof for
    provenance proof. What it will never do is accept a credential from the JSON
    SSO caches or another product's store, which is what let one Builder ID
    account's leftover token be served as a different Builder ID account's balance.

    Returns the canonical usage dict on success, or None on ANY failure (no
    token, no candidate proven, unparseable body, no CREDIT breakdown). The caller
    treats None as "fall back to the text scrape". This function never raises and
    never logs the token (controls 4 & 5).

    The ``auth_state`` alongside it says whether that None was AUTH-CLASS -- see
    :data:`AUTH_NO_CREDENTIAL` and :data:`AUTH_REJECTED` -- so the caller can tell
    the user to sign in again instead of reporting the account has no credit plan.
    It is classified from the
    enumeration this function already performs: no store is read a second time,
    no new credential source is consulted, and nothing about who may read or
    refresh a token changes.

    Call from async code via ``asyncio.get_running_loop().run_in_executor(...)``
    so the blocking HTTP call does not stall the event loop.
    """
    return _supplier_usage()
