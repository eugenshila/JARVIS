from fastapi.testclient import TestClient

from jarvis.server import api


def test_hud_chat_sends_history_to_fixed_local_model(monkeypatch):
    captured = {}

    def fake_request(path, payload=None):
        captured.update(path=path, payload=payload)
        return {"message": {"content": "At your service."}}

    monkeypatch.setattr(api, "_ollama_request", fake_request)
    response = TestClient(api.app).post("/hud/chat", json={"messages": [
        {"role": "user", "content": "Remember the plan?"},
        {"role": "assistant", "content": "Yes."},
        {"role": "user", "content": "What next?"},
    ]})
    assert response.status_code == 200
    assert response.json()["content"] == "At your service."
    assert captured["path"] == "/api/chat"
    assert captured["payload"]["model"] == "qwen2.5:3b"
    assert [m["role"] for m in captured["payload"]["messages"]] == ["system", "user", "assistant", "user"]


def test_hud_status_reports_missing_model(monkeypatch):
    monkeypatch.setattr(api, "_ollama_request", lambda path, payload=None: {"models": [{"name": "llama3.2:3b"}]})
    response = TestClient(api.app).get("/hud/status")
    assert response.json()["ollama"] == "model_missing"
