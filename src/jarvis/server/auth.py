"""
server/auth.py — a token on the API, because there wasn't one.

THE SITUATION BEFORE
    ``jarvis.server.api`` exposed shell-capable agents, memory, connectors and
    the confirmation gate with **no authentication at all**. Bound to
    localhost that is merely untidy; the moment anyone runs it on ``0.0.0.0``
    to reach the HUD from a phone — which the launcher scripts encourage — it
    is an unauthenticated remote code execution endpoint on the LAN.

THE DESIGN
    A bearer token, checked by middleware, compared with
    :func:`secrets.compare_digest`:

    * The token is generated once into ``~/.jarvis/api_token`` with 0600
      permissions, or taken from ``JARVIS_API_TOKEN``.
    * Requests present it as ``Authorization: Bearer <token>`` or
      ``X-Jarvis-Token``. A ``?token=`` query parameter is accepted too,
      because browsers cannot set headers on EventSource/WebSocket URLs.
    * **Loopback requests are exempt by default** so existing local workflows,
      the CLI and the desktop shell keep working untouched. The moment the
      server is reachable off-box, remote callers need the token.
      ``JARVIS_API_REQUIRE_TOKEN=1`` removes the loopback exemption;
      ``JARVIS_API_AUTH=off`` disables the whole thing for a trusted setup.
    * ``/health`` and the OpenAPI docs stay open so a reverse proxy can probe
      the service.

    Why a token rather than the application-layer AES the design this came
    from uses: encrypting a payload does not authenticate a caller, and it
    leaves the key in browser JavaScript. A token over loopback or a TLS
    terminator is both simpler and stronger. Do not expose this to the open
    internet without TLS in front of it.
"""

from __future__ import annotations

import ipaddress
import os
import secrets
from pathlib import Path

TOKEN_FILENAME = "api_token"
TOKEN_ENV = "JARVIS_API_TOKEN"

#: Never require a token for these — a proxy has to be able to health-check.
OPEN_PATHS = frozenset({"/health", "/docs", "/redoc", "/openapi.json", "/favicon.ico"})


def _token_path() -> Path:
    from jarvis.core.config import get_home

    return get_home() / TOKEN_FILENAME


def auth_enabled() -> bool:
    return os.environ.get("JARVIS_API_AUTH", "on").strip().lower() not in ("off", "0", "false")


def loopback_exempt() -> bool:
    """True when local callers skip the token (the default)."""
    return os.environ.get("JARVIS_API_REQUIRE_TOKEN", "").strip().lower() not in ("1", "true", "yes")


def get_token(create: bool = True) -> str:
    """The current API token, generated and persisted on first use."""
    from_env = os.environ.get(TOKEN_ENV, "").strip()
    if from_env:
        return from_env

    path = _token_path()
    try:
        existing = path.read_text(encoding="utf-8").strip()
        if existing:
            return existing
    except OSError:
        pass

    if not create:
        return ""

    token = secrets.token_urlsafe(32)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(token, encoding="utf-8")
        os.chmod(path, 0o600)  # not world-readable on a shared machine
    except OSError:
        pass
    return token


def rotate_token() -> str:
    """Issue a new token, invalidating every existing client."""
    token = secrets.token_urlsafe(32)
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(token, encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return token


def is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host in ("localhost", "testclient"):  # TestClient has no real socket
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def presented_token(headers, query_params) -> str:
    """Pull the token out of a request, in header-then-query order."""
    authorization = headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    header_token = headers.get("x-jarvis-token", "")
    if header_token:
        return header_token.strip()
    try:
        return (query_params.get("token") or "").strip()
    except Exception:
        return ""


def check(path: str, client_host: str | None, headers, query_params) -> tuple[bool, str]:
    """Returns ``(allowed, reason_if_denied)``."""
    if not auth_enabled():
        return True, ""
    if path in OPEN_PATHS:
        return True, ""
    if loopback_exempt() and is_loopback(client_host):
        return True, ""

    supplied = presented_token(headers, query_params)
    if not supplied:
        return False, (
            "Missing API token. Send 'Authorization: Bearer <token>'. "
            "Find yours with `jarvis token`."
        )
    if not secrets.compare_digest(supplied, get_token()):
        return False, "Invalid API token."
    return True, ""


def install(app) -> None:
    """Attach the middleware to a FastAPI app."""
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def _require_token(request, call_next):  # pragma: no cover - exercised via TestClient
        allowed, reason = check(
            request.url.path,
            request.client.host if request.client else None,
            request.headers,
            request.query_params,
        )
        if not allowed:
            return JSONResponse(status_code=401, content={"detail": reason})
        return await call_next(request)
