"""HTTP action bridge for the Shilatech Autospares web application.

The bridge uses Shilatech's existing API and authorization rules. Credentials are
read only from environment variables and are never accepted as tool arguments.
"""
from __future__ import annotations

import json
import os
import ssl
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import HTTPCookieProcessor, HTTPSHandler, Request, build_opener


SECTIONS = {
    "dashboard": "/api/admin/overview",
    "shop": "/api/products",
    "orders": "/api/orders",
    "operations": "/api/admin/operations",
    "warehouse": "/api/warehouse/overview",
    "delivery": "/api/delivery/overview",
    "pos": "/api/pos",
    "workshop": "/api/staff-garage",
    "finance": "/api/finance-ledger",
    "receivables": "/api/receivables",
    "payroll": "/api/payroll",
    "hr": "/api/hr-records",
    "my_hr": "/api/hr",
    "approvals": "/api/approvals",
    "garage": "/api/garage",
    "vin": "/api/vin",
}

# Mutations involving payment initiation or authentication are intentionally absent.
MUTABLE_SECTIONS = {
    "orders", "operations", "warehouse", "delivery", "pos", "workshop",
    "finance", "receivables", "payroll", "hr", "my_hr", "approvals", "garage",
}


def _base_url() -> str:
    value = os.environ.get("SHILATECH_URL", "").strip().rstrip("/")
    if not value:
        raise RuntimeError("SHILATECH_URL is not configured.")
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RuntimeError("SHILATECH_URL must be an absolute HTTP(S) URL.")
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1", "0.0.0.0"}:
        raise RuntimeError("SHILATECH_URL must use HTTPS except during local development.")
    return value


def _decode(response) -> dict | list:
    raw = response.read(2_000_001)
    if len(raw) > 2_000_000:
        raise RuntimeError("Shilatech response exceeded the 2 MB safety limit.")
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Shilatech returned an invalid JSON response.") from exc


def _request(opener, url: str, method: str = "GET", body: dict | None = None):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json", "User-Agent": "JARVIS-Shilatech/1.0"}
    if data is not None:
        headers.update({"Content-Type": "application/json", "Sec-Fetch-Site": "same-origin"})
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with opener.open(request, timeout=30) as response:
            return _decode(response)
    except HTTPError as exc:
        try:
            detail = _decode(exc)
            message = detail.get("error") if isinstance(detail, dict) else str(detail)
        except Exception:
            message = exc.reason
        raise RuntimeError(f"Shilatech API returned {exc.code}: {message}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Shilatech: {exc.reason}") from exc


def _client(base: str):
    context = ssl.create_default_context()
    opener = build_opener(HTTPCookieProcessor(CookieJar()), HTTPSHandler(context=context))
    cookie = os.environ.get("SHILATECH_SESSION_COOKIE", "").strip()
    if cookie:
        opener.addheaders = [("Cookie", cookie)]
        return opener

    email = os.environ.get("SHILATECH_EMAIL", "").strip()
    password = os.environ.get("SHILATECH_PASSWORD", "")
    if email and password:
        _request(opener, base + "/api/auth/login", "POST", {
            "email": email, "password": password, "staffOnly": True,
        })
    return opener


def shilatech_action(parameters: dict, player=None) -> str:
    """Run an operation corresponding to a Shilatech page/department."""
    section = str(parameters.get("section") or "shop").strip().lower()
    action = str(parameters.get("action") or "view").strip().lower()
    if section not in SECTIONS:
        raise ValueError("Unknown Shilatech section. Use dashboard, shop, orders, operations, warehouse, delivery, pos, workshop, finance, receivables, payroll, hr, my_hr, approvals, garage, or vin.")

    base = _base_url()
    opener = _client(base)
    query = parameters.get("query") or {}
    if not isinstance(query, dict):
        raise ValueError("query must be an object")
    # Empty values are omitted and all query data is safely URL encoded.
    query = {str(k): str(v).lower() if isinstance(v, bool) else str(v)
             for k, v in query.items() if v not in (None, "")}
    path = SECTIONS[section]
    url = base + path + (("?" + urlencode(query)) if query else "")

    if action in {"view", "list", "search", "lookup", "receipt"}:
        result = _request(opener, url)
    elif action in {"create", "update", "submit", "process"}:
        if section not in MUTABLE_SECTIONS:
            raise ValueError(f"The {section} section is read-only through JARVIS.")
        if parameters.get("confirmed") is not True:
            raise ValueError("This changes Shilatech data. Repeat with confirmed=true only after the user explicitly confirms the exact change.")
        payload = parameters.get("payload")
        if not isinstance(payload, dict) or not payload:
            raise ValueError("A non-empty payload object is required for this action.")
        result = _request(opener, url, "POST", payload)
    else:
        raise ValueError("Unsupported action. Use view/list/search/lookup, or an explicitly confirmed create/update/submit/process action.")

    return json.dumps({"section": section, "action": action, "data": result}, ensure_ascii=False, default=str, indent=2)
