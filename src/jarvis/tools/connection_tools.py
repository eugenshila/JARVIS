"""Connection/status tools for calendar and email integrations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jarvis.core.config import get_home
from jarvis.tools.base import BaseTool, ToolSpec


class ConnectionStatusTool(BaseTool):
    spec = ToolSpec(
        name="connections",
        description=(
            "Show or start setup for calendar/email connections. Supports Google Calendar/Gmail now, "
            "local JSON fallback, and Microsoft Outlook/365 setup guidance."
        ),
        parameters={
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["status", "google_instructions", "google_setup", "microsoft_instructions", "local_paths"],
                    "default": "status",
                }
            },
            "required": [],
        },
    )

    def run(self, action: str = "status", **kwargs: Any) -> str:
        action = (action or "status").lower()
        if action == "google_instructions":
            return self.google_instructions()
        if action == "google_setup":
            return self.google_setup()
        if action == "microsoft_instructions":
            return self.microsoft_instructions()
        if action == "local_paths":
            return self.local_paths()
        return self.status()

    def status(self) -> str:
        home = get_home()
        calendar_path = home / "calendar.json"
        emails_path = home / "emails.json"

        lines = ["**JARVIS Connections — Calendar + Email**", ""]
        try:
            from jarvis.connectors.google import GoogleConnector

            google = GoogleConnector()
            lines.extend([
                "**Google Calendar/Gmail:**",
                f"  • Credentials: {'✅ found' if google.is_configured() else '⚠️ missing'} — {google.creds_path}",
                f"  • OAuth token: {'✅ authenticated' if google.is_authenticated() else '⚠️ not authenticated'} — {google.token_path}",
            ])
            if google.is_authenticated():
                lines.append("  • Status: real Google Calendar/Gmail reads are enabled for morning briefing.")
            elif google.is_configured():
                lines.append("  • Next: run `jarvis connect google --setup` to sign in once.")
            else:
                lines.append("  • Next: run `jarvis connect google --instructions` for OAuth setup.")
        except Exception as exc:
            lines.extend(["**Google Calendar/Gmail:**", f"  • Connector unavailable: {exc}"])

        lines.extend([
            "",
            "**Microsoft Outlook/Office 365:**",
            "  • Status: guidance available; Graph OAuth implementation is the next connector.",
            "  • Next: `jarvis connect microsoft --instructions` if Outlook is your main account.",
            "",
            "**Local fallback:**",
            f"  • Calendar file: {'✅ found' if calendar_path.exists() else '⚠️ not created'} — {calendar_path}",
            f"  • Email file: {'✅ found' if emails_path.exists() else '⚠️ not created'} — {emails_path}",
            "",
            "Privacy default: Read-only. JARVIS should ask before sending mail, deleting messages, or creating events.",
        ])
        return "\n".join(lines)

    def google_instructions(self) -> str:
        try:
            from jarvis.connectors.google import GoogleConnector

            return GoogleConnector().setup_instructions()
        except Exception as exc:
            return f"Google connector failed to load: {exc}"

    def google_setup(self) -> str:
        try:
            from jarvis.connectors.google import GoogleConnector

            return GoogleConnector().setup()
        except Exception as exc:
            return f"Google setup failed before OAuth could start: {exc}"

    def microsoft_instructions(self) -> str:
        return """**Microsoft Outlook / Office 365 Setup — Planned Connector**

For Outlook calendar/email, JARVIS should use Microsoft Graph OAuth with read-only scopes first:

Required Azure app settings:
  1. Go to https://portal.azure.com/ → Microsoft Entra ID → App registrations
  2. New registration: JARVIS Desktop
  3. Supported account types: choose personal/work as needed
  4. Redirect URI: Public client/native app, http://localhost
  5. API permissions, delegated:
     • Calendars.Read
     • Mail.Read
     • User.Read
  6. Enable public client flows
  7. Save the Application/Client ID locally in ~/.jarvis/microsoft.json

Safety policy:
  • Start read-only: read calendar and unread mail for briefings
  • Sending email or creating events must require explicit confirmation
  • No password storage — OAuth token only, in your local JARVIS folder

Implementation status: Google OAuth is available now; Microsoft Graph is the next connector to wire into the same Connections screen.
"""

    def local_paths(self) -> str:
        home = get_home()
        home.mkdir(parents=True, exist_ok=True)
        return f"""**Local Calendar/Email Fallback**

Use these files if you want offline/manual data without Google or Microsoft OAuth:

Calendar: {home / 'calendar.json'}
Example:
[
  {{"date": "2026-09-28", "time": "10:00 AM", "title": "Planning meeting"}}
]

Email: {home / 'emails.json'}
Example:
[
  {{"from": "client@example.com", "subject": "Need reply", "time": "09:30", "unread": true, "important": true}}
]

JARVIS reads these locally for morning briefing and task alignment.
"""
