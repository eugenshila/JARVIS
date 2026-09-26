"""Minimal OpenAI compatible chat client using only Python's standard library."""

import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def generate(prompt: str, context: str) -> str:
    # Deterministic offline path used by tests and supported for local smoke checks.
    if os.environ.get("JARVIS_MOCK", "").strip().lower() in {"1", "true", "yes", "on"}:
        return f"Mock response for: {prompt}"

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise ValueError("Set OPENAI_API_KEY to enable AI responses, or use Copy prompt.")
    url = os.environ.get("JARVIS_API_URL", "https://api.openai.com/v1/chat/completions")
    if not url.startswith("https://"):
        raise ValueError("JARVIS_API_URL must use HTTPS.")
    payload = {
        "model": os.environ.get("JARVIS_MODEL", "gpt-4o-mini"),
        "messages": [
            {"role": "system", "content": "Use only supplied context for personal facts. Mark inferences clearly. Never invent meeting details."},
            {"role": "user", "content": f"{prompt}\n\nMeeting or task context:\n{context or '(No context supplied)'}"},
        ],
    }
    request = Request(url, data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"API returned HTTP {error.code}. Check your key, model and provider.") from error
    except URLError as error:
        raise RuntimeError(f"Could not connect to the API: {error.reason}") from error
    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError("The API returned an unexpected response format.") from error
