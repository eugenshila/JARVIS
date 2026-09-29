"""The interface half of the confirmation gate.

`jarvis/core/confirm.py` refuses to run irreversible work until a human
approves it. That is only a gate if a human can actually see the request and
press a button, so these tests cover the three surfaces that must stay wired:

  * the HTTP endpoints the browser HUD calls,
  * the React component that renders CONFIRM / CANCEL,
  * the Tk desktop HUD that ships in the MSI and runs the agent in-process.

The React and Tk checks are deliberately source-level: neither a browser nor
an X server exists in CI, and a silently unmounted component is exactly the
regression that left this gate unusable before.
"""

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _clean_gate():
    from jarvis.core import confirm as confirm_gate

    confirm_gate.clear()
    yield
    confirm_gate.clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from jarvis.server import api

    return TestClient(api.app)


# ── HTTP surface ──────────────────────────────────────────────────────────────

def test_pending_request_is_visible_to_the_hud(client):
    from jarvis.core import confirm as confirm_gate

    confirm_gate.request("Run shell command", "rm -rf ./build", lambda: "done")

    body = client.get("/confirm").json()
    item = body["pending"][0]
    assert item["title"] == "Run shell command"
    assert item["detail"] == "rm -rf ./build"
    assert 0 < item["expires_in"] <= confirm_gate.TIMEOUT_SECONDS
    assert item["token"]


def test_nothing_runs_until_a_human_approves(client):
    from jarvis.core import confirm as confirm_gate

    ran = []
    entry = confirm_gate.request("Launch", "calculator", lambda: (ran.append(1), "launched")[1])

    # Merely looking at the queue must not run the work.
    client.get("/confirm")
    assert ran == []

    approved = client.post(f"/confirm/{entry.token}/approve")
    assert approved.status_code == 200
    assert approved.json()["result"] == "launched"
    assert ran == [1]


def test_an_approved_token_cannot_be_replayed(client):
    from jarvis.core import confirm as confirm_gate

    ran = []
    entry = confirm_gate.request("Launch", "calculator", lambda: (ran.append(1), "launched")[1])

    assert client.post(f"/confirm/{entry.token}/approve").status_code == 200
    second = client.post(f"/confirm/{entry.token}/approve")
    assert second.status_code == 404
    assert ran == [1]  # a double-click does not run it twice


def test_cancel_drops_the_work_and_empties_the_queue(client):
    from jarvis.core import confirm as confirm_gate

    ran = []
    entry = confirm_gate.request("Launch", "calculator", lambda: ran.append(1))

    assert client.post(f"/confirm/{entry.token}/cancel").status_code == 200
    assert client.get("/confirm").json()["pending"] == []
    assert ran == []
    assert client.post(f"/confirm/{entry.token}/cancel").status_code == 404


def test_unknown_token_is_rejected(client):
    assert client.post("/confirm/not-a-real-token/approve").status_code == 404


# ── React HUD ─────────────────────────────────────────────────────────────────

CONFIRM_GATE_TSX = ROOT / "frontend" / "src" / "components" / "ConfirmGate.tsx"


def test_react_confirm_gate_exists_and_talks_to_the_gate_endpoints():
    source = CONFIRM_GATE_TSX.read_text(encoding="utf-8")
    assert "fetch('/confirm'" in source
    assert "/approve" in source and "/cancel" in source
    assert "CONFIRM" in source and "CANCEL" in source


def test_react_confirm_gate_is_mounted_for_every_view():
    """Mounted outside <App> so it shows on the dashboard, the HUD and chat."""
    main_tsx = (ROOT / "frontend" / "src" / "main.tsx").read_text(encoding="utf-8")
    assert "ConfirmGate" in main_tsx
    assert "<ConfirmGate />" in main_tsx


def test_dev_server_proxies_the_gate_endpoints_to_the_api():
    vite = (ROOT / "frontend" / "vite.config.ts").read_text(encoding="utf-8")
    assert "'/confirm'" in vite


# ── Tk desktop HUD (what the MSI ships) ───────────────────────────────────────

def test_desktop_hud_polls_and_exposes_confirm_and_cancel():
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    for needle in (
        "def poll_confirmations",
        "def approve_confirmation",
        "def cancel_confirmation",
        "confirm_gate.resolve",
        "confirm_gate.cancel",
        "self.after(1000, self.poll_confirmations)",
    ):
        assert needle in source, f"desktop HUD lost its confirmation affordance: {needle}"


def test_desktop_hud_runs_approved_work_off_the_ui_thread():
    """A confirmed shell command can take seconds; Tk must not freeze."""
    source = (ROOT / "app.py").read_text(encoding="utf-8")
    approve = source.split("def approve_confirmation")[1].split("def cancel_confirmation")[0]
    assert "threading.Thread" in approve
    assert "daemon=True" in approve
