"""Home Assistant connector — controls everything (lights, switches, media, etc).

Setup:
  1. Get HA URL and long-lived access token: HA → Profile → Long-Lived Access Tokens → Create
  2. Set env: HASS_URL=http://homeassistant.local:8123, HASS_TOKEN=your_token
  3. Or save to ~/.jarvis/hass.json

Usage:
  from jarvis.connectors.homeassistant import HomeAssistantConnector
  ha = HomeAssistantConnector()
  ha.call_service("light", "turn_on", entity_id="light.lab", brightness=100, color_name="blue")
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jarvis.core.config import get_home


class HomeAssistantConnector:
    def __init__(self, url: str | None = None, token: str | None = None):
        self.home = get_home()
        self.config_path = self.home / "hass.json"
        self.url = url
        self.token = token
        self._load_config()

    def _load_config(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.url = self.url or data.get("url")
                self.token = self.token or data.get("token")
            except Exception:
                pass
        self.url = self.url or os.environ.get("HASS_URL") or os.environ.get("HOMEASSISTANT_URL")
        self.token = self.token or os.environ.get("HASS_TOKEN") or os.environ.get("HOMEASSISTANT_TOKEN")
        if self.url:
            self.url = self.url.rstrip("/")

    def _save_config(self):
        self.home.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({
            "url": self.url,
            "token": "***" if self.token else None,  # Don't save token in plain text by default, use env
        }, indent=2))

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def call_service(self, domain: str, service: str, entity_id: str | None = None, **kwargs) -> dict[str, Any]:
        """Call HA service, e.g., light.turn_on, switch.turn_off."""
        if not self.url or not self.token:
            raise RuntimeError("HASS_URL and HASS_TOKEN not set. Set env or ~/.jarvis/hass.json")

        import urllib.request
        import urllib.error

        url = f"{self.url}/api/services/{domain}/{service}"
        data: dict[str, Any] = {}
        if entity_id:
            data["entity_id"] = entity_id
        data.update(kwargs)

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode(),
            headers=self._headers(),
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:500]
            raise RuntimeError(f"HA HTTP {e.code}: {body}") from e
        except urllib.error.URLError as e:
            raise RuntimeError(f"HA not reachable at {self.url}: {e.reason}") from e

    def get_states(self, entity_id: str | None = None) -> Any:
        """Get states, optionally filtered by entity_id."""
        if not self.url or not self.token:
            raise RuntimeError("HASS_URL and HASS_TOKEN not set")

        import urllib.request

        if entity_id:
            url = f"{self.url}/api/states/{entity_id}"
        else:
            url = f"{self.url}/api/states"

        req = urllib.request.Request(url, headers=self._headers())
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    def list_lights(self) -> list[dict[str, Any]]:
        try:
            states = self.get_states()
            lights = [s for s in states if s["entity_id"].startswith("light.")]
            return [{"entity_id": l["entity_id"], "state": l["state"], "name": l["attributes"].get("friendly_name", l["entity_id"])} for l in lights]
        except Exception as e:
            return [{"entity_id": "light.lab_mock", "state": "on", "name": f"Lab (mock, HA not connected: {e})"}]

    def turn_on_light(self, entity_id: str = "all", brightness: int | None = None, color_name: str | None = None, rgb_color: list[int] | None = None) -> str:
        try:
            kwargs: dict[str, Any] = {}
            if brightness is not None:
                kwargs["brightness"] = max(1, min(255, int(brightness * 255 / 100)))
            if color_name:
                kwargs["color_name"] = color_name
            if rgb_color:
                kwargs["rgb_color"] = rgb_color

            if entity_id == "all":
                # Turn on all lights
                lights = self.list_lights()
                for light in lights:
                    if "mock" not in light["entity_id"]:
                        self.call_service("light", "turn_on", entity_id=light["entity_id"], **kwargs)
                return f"Turned on {len(lights)} lights via Home Assistant"
            else:
                # Fuzzy match entity_id
                if not entity_id.startswith("light."):
                    # Try to find matching light
                    lights = self.list_lights()
                    for light in lights:
                        if entity_id.lower() in light["entity_id"].lower() or entity_id.lower() in light["name"].lower():
                            entity_id = light["entity_id"]
                            break
                    if not entity_id.startswith("light."):
                        entity_id = f"light.{entity_id.lower().replace(' ', '_')}"

                self.call_service("light", "turn_on", entity_id=entity_id, **kwargs)
                return f"Turned on {entity_id} via Home Assistant"
        except Exception as e:
            return f"HA light control failed (mock fallback): {e}. Set HASS_URL and HASS_TOKEN env"

    def turn_off_light(self, entity_id: str = "all") -> str:
        try:
            if entity_id == "all":
                self.call_service("light", "turn_off", entity_id="all")
                return "Turned off all lights via Home Assistant"
            else:
                if not entity_id.startswith("light."):
                    entity_id = f"light.{entity_id.lower().replace(' ', '_')}"
                self.call_service("light", "turn_off", entity_id=entity_id)
                return f"Turned off {entity_id} via Home Assistant"
        except Exception as e:
            return f"HA light off failed: {e}"

    def play_media(self, entity_id: str = "media_player.lab", media_content_id: str = "", media_content_type: str = "music") -> str:
        try:
            self.call_service("media_player", "play_media", entity_id=entity_id, media_content_id=media_content_id, media_content_type=media_content_type)
            return f"Playing {media_content_id} on {entity_id} via HA"
        except Exception as e:
            return f"HA media play failed: {e}"

    def get_status(self) -> str:
        try:
            states = self.get_states()
            lights = [s for s in states if s["entity_id"].startswith("light.")]
            switches = [s for s in states if s["entity_id"].startswith("switch.")]
            return f"Home Assistant at {self.url}: {len(lights)} lights, {len(switches)} switches, {len(states)} total entities"
        except Exception as e:
            return f"HA not connected: {e}. Set HASS_URL and HASS_TOKEN"
