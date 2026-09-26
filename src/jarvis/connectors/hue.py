"""Philips Hue connector — real smart lights control.

Setup:
  1. Find Hue Bridge IP: https://discovery.meethue.com/ or check router
  2. Press button on Hue Bridge
  3. Run: python -m jarvis.connectors.hue --bridge-ip 192.168.1.2 --setup
  4. Saves config to ~/.jarvis/hue.json

Usage:
  from jarvis.connectors.hue import HueConnector
  hue = HueConnector()
  hue.lights_on("Lab", brightness=100, color="blue")
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from jarvis.core.config import get_home


class HueConnector:
    def __init__(self, bridge_ip: str | None = None, username: str | None = None):
        self.home = get_home()
        self.config_path = self.home / "hue.json"
        self.bridge_ip = bridge_ip
        self.username = username
        self._load_config()
        self._bridge = None

    def _load_config(self):
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                self.bridge_ip = self.bridge_ip or data.get("bridge_ip")
                self.username = self.username or data.get("username")
            except Exception:
                pass
        # Env overrides
        self.bridge_ip = self.bridge_ip or os.environ.get("HUE_BRIDGE_IP")
        self.username = self.username or os.environ.get("HUE_USERNAME")

    def _save_config(self):
        self.home.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({
            "bridge_ip": self.bridge_ip,
            "username": self.username,
        }, indent=2))

    def setup(self, bridge_ip: str) -> str:
        """First-time setup — press button on bridge, then call this."""
        self.bridge_ip = bridge_ip
        try:
            from phue import Bridge  # type: ignore
            b = Bridge(bridge_ip)
            b.connect()  # Press button on bridge before this
            self.username = b.username
            self._save_config()
            return f"Connected to Hue Bridge at {bridge_ip}, username {self.username} saved to {self.config_path}"
        except ImportError:
            return "phue not installed. Run: pip install phue"
        except Exception as e:
            return f"Setup failed (did you press button on bridge?): {e}"

    def _get_bridge(self):
        if self._bridge:
            return self._bridge
        if not self.bridge_ip:
            raise RuntimeError("Hue Bridge IP not set. Run setup or set HUE_BRIDGE_IP env")
        try:
            from phue import Bridge
            self._bridge = Bridge(self.bridge_ip, self.username)
            self._bridge.connect()
            return self._bridge
        except ImportError as e:
            raise RuntimeError("phue not installed: pip install phue") from e
        except Exception as e:
            raise RuntimeError(f"Failed to connect to Hue Bridge {self.bridge_ip}: {e}") from e

    def list_lights(self) -> list[dict[str, Any]]:
        try:
            b = self._get_bridge()
            lights = b.get_light_objects('id')
            result = []
            for light_id, light in lights.items():
                result.append({
                    "id": light_id,
                    "name": light.name,
                    "on": light.on,
                    "brightness": light.brightness,
                })
            return result
        except Exception as e:
            # Fallback to mock if real fails
            return [{"id": 1, "name": "Lab (mock, Hue not connected)", "on": True, "brightness": 100, "error": str(e)}]

    def set_light(self, name: str, on: bool | None = None, brightness: int | None = None, color: str | None = None, rgb: tuple[int,int,int] | None = None) -> str:
        """Set light by name (or 'all')."""
        try:
            b = self._get_bridge()
            # Find lights matching name
            lights = b.get_light_objects('name')
            targets = []
            if name.lower() == "all":
                targets = list(lights.values())
            else:
                # Fuzzy match
                for light_name, light in lights.items():
                    if name.lower() in light_name.lower() or light_name.lower() in name.lower():
                        targets.append(light)
                if not targets and name in lights:
                    targets = [lights[name]]

            if not targets:
                return f"No Hue lights matching '{name}'. Available: {list(lights.keys())}"

            for light in targets:
                if on is not None:
                    light.on = on
                if brightness is not None:
                    light.brightness = max(1, min(254, int(brightness * 254 / 100)))
                if color:
                    # Simple color mapping
                    color_map = {
                        "red": [0.675, 0.322],
                        "blue": [0.167, 0.04],
                        "green": [0.2151, 0.7106],
                        "white": [0.3127, 0.329],
                        "warm": [0.5, 0.4],
                    }
                    if color.lower() in color_map:
                        light.xy = color_map[color.lower()]
                if rgb:
                    # Convert RGB to XY (simplified)
                    light.xy = self._rgb_to_xy(*rgb)

            return f"Set {len(targets)} Hue light(s) matching '{name}': on={on}, brightness={brightness}, color={color}"
        except Exception as e:
            return f"Hue control failed (using mock fallback): {e}. To enable real Hue: pip install phue and set HUE_BRIDGE_IP"

    def _rgb_to_xy(self, r: int, g: int, b: int) -> list[float]:
        # Simplified RGB to XY conversion
        # Real conversion is more complex, this is approximate
        r, g, b = r/255.0, g/255.0, b/255.0
        # Gamma correction
        r = pow((r + 0.055) / 1.055, 2.4) if r > 0.04045 else r / 12.92
        g = pow((g + 0.055) / 1.055, 2.4) if g > 0.04045 else g / 12.92
        b = pow((b + 0.055) / 1.055, 2.4) if b > 0.04045 else b / 12.92
        X = r * 0.664511 + g * 0.154324 + b * 0.162028
        Y = r * 0.283881 + g * 0.668433 + b * 0.047685
        Z = r * 0.000088 + g * 0.072310 + b * 0.986039
        if X + Y + Z == 0:
            return [0.3127, 0.329]
        x = X / (X + Y + Z)
        y = Y / (X + Y + Z)
        return [x, y]


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Hue setup")
    parser.add_argument("--bridge-ip", help="Hue Bridge IP")
    parser.add_argument("--setup", action="store_true", help="Press button on bridge, then setup")
    parser.add_argument("--list", action="store_true", help="List lights")
    parser.add_argument("--on", help="Turn on light by name")
    parser.add_argument("--off", help="Turn off light by name")
    args = parser.parse_args()

    hue = HueConnector()
    if args.setup and args.bridge_ip:
        print(hue.setup(args.bridge_ip))
    elif args.list:
        print(json.dumps(hue.list_lights(), indent=2))
    elif args.on:
        print(hue.set_light(args.on, on=True))
    elif args.off:
        print(hue.set_light(args.off, on=False))
    else:
        parser.print_help()
