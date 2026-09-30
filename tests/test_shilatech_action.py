from __future__ import annotations

import json

import pytest

from actions import shilatech


def setup_client(monkeypatch):
    monkeypatch.setenv("SHILATECH_URL", "https://autospares.example")
    monkeypatch.setattr(shilatech, "_client", lambda base: object())


def test_shop_search_maps_filters_to_products_api(monkeypatch):
    setup_client(monkeypatch)
    calls = []

    def fake_request(opener, url, method="GET", body=None):
        calls.append((url, method, body))
        return {"products": []}

    monkeypatch.setattr(shilatech, "_request", fake_request)
    result = json.loads(shilatech.shilatech_action({
        "section": "shop", "action": "search",
        "query": {"q": "brake pad", "brand": "Jeep", "inStock": True},
    }))
    assert result["section"] == "shop"
    assert calls[0][1] == "GET"
    assert "/api/products?" in calls[0][0]
    assert "q=brake+pad" in calls[0][0]
    assert "inStock=true" in calls[0][0]


def test_mutation_requires_explicit_confirmation(monkeypatch):
    setup_client(monkeypatch)
    monkeypatch.setattr(shilatech, "_request", lambda *args, **kwargs: {})
    with pytest.raises(ValueError, match="confirmed=true"):
        shilatech.shilatech_action({
            "section": "workshop", "action": "update", "payload": {"id": 7},
        })


def test_confirmed_mutation_posts_exact_payload(monkeypatch):
    setup_client(monkeypatch)
    calls = []
    monkeypatch.setattr(shilatech, "_request", lambda opener, url, method="GET", body=None: calls.append((method, body)) or {"ok": True})
    payload = {"action": "UPDATE", "id": 7, "notes": "Ready"}
    shilatech.shilatech_action({
        "section": "workshop", "action": "update", "payload": payload, "confirmed": True,
    })
    assert calls == [("POST", payload)]


def test_non_https_remote_url_is_rejected(monkeypatch):
    monkeypatch.setenv("SHILATECH_URL", "http://autospares.example")
    with pytest.raises(RuntimeError, match="must use HTTPS"):
        shilatech.shilatech_action({"section": "shop", "action": "view"})
