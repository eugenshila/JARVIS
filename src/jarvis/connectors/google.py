"""Google Calendar + Gmail real OAuth integration for Good Morning Eugene.

Setup:
1. Go to https://console.cloud.google.com/
2. Create project, enable Calendar API + Gmail API
3. Create OAuth consent screen + Desktop app credentials
4. Download credentials.json to ~/.jarvis/google_credentials.json
5. Run: python -m jarvis.connectors.google --setup
6. Browser opens, login, saves token to ~/.jarvis/google_token.json
7. Then calendar + email real work

For ADHD + Iron Man: Good Morning Eugene with real events + real unread + tasks from emails auto.

No credentials.json? Falls back to mock + local files.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any

from jarvis.core.config import get_home


class GoogleConnector:
    def __init__(self):
        self.home = get_home()
        self.creds_path = self.home / "google_credentials.json"
        self.token_path = self.home / "google_token.json"
        self.calendar_path = self.home / "calendar.json"
        self.emails_path = self.home / "emails.json"

    def is_configured(self) -> bool:
        return self.creds_path.exists()

    def is_authenticated(self) -> bool:
        return self.token_path.exists()

    def setup_instructions(self) -> str:
        return """
**Google Calendar + Gmail Setup for Good Morning Eugene:**

1. Go to https://console.cloud.google.com/
2. Create project: JARVIS
3. Enable APIs:
   - Google Calendar API
   - Gmail API
4. OAuth consent screen:
   - User type: External
   - App name: JARVIS
   - Scopes: calendar.readonly, gmail.readonly
   - Test users: add your email
5. Credentials:
   - Create Credentials → OAuth client ID → Desktop app → Name: JARVIS Desktop
   - Download JSON → Save as ~/.jarvis/google_credentials.json
6. Setup:
   python -m jarvis.connectors.google --setup
   # Browser opens, login, saves token to ~/.jarvis/google_token.json
7. Done! Good Morning Eugene now shows real events + emails

No setup? JARVIS uses mock + local files:
  • ~/.jarvis/calendar.json for events
  • ~/.jarvis/emails.json for emails
  • Say 'calendar add Q4 meeting at 2pm'
  • Say 'email add client@example.com needs reply'

For quick local without Google:
  • Just use local files, no OAuth needed
"""

    def setup(self) -> str:
        """OAuth flow — browser login."""
        if not self.creds_path.exists():
            return f"credentials.json not found at {self.creds_path}\n\n{self.setup_instructions()}"

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            SCOPES = [
                'https://www.googleapis.com/auth/calendar.readonly',
                'https://www.googleapis.com/auth/gmail.readonly'
            ]

            creds = None
            if self.token_path.exists():
                creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                else:
                    flow = InstalledAppFlow.from_client_secrets_file(str(self.creds_path), SCOPES)
                    creds = flow.run_local_server(port=0)
                
                self.token_path.write_text(creds.to_json())
                return f"✅ Google auth saved to {self.token_path}\n\nNow Good Morning Eugene shows real calendar + emails, Sir."

            return f"Already authenticated, token at {self.token_path}"

        except ImportError:
            return "Need google-auth-oauthlib: pip install google-auth-oauthlib google-api-python-client google-auth"
        except Exception as e:
            return f"Google setup failed: {e}\n\n{self.setup_instructions()}"

    def get_calendar_today(self) -> List[Dict[str, Any]]:
        """Get today's calendar events — real Google or local mock."""
        today_str = datetime.now().date().isoformat()
        
        # Try real Google Calendar
        if self.is_authenticated():
            try:
                return self._get_google_calendar_today()
            except Exception as e:
                print(f"Google Calendar failed: {e}, using local")

        # Local file
        if self.calendar_path.exists():
            try:
                events = json.loads(self.calendar_path.read_text())
                today_events = [e for e in events if e.get("date") == today_str]
                if today_events:
                    return today_events
            except:
                pass

        # Mock
        return [
            {"time": "10:00 AM", "title": "Q4 Planning Prep", "date": today_str, "duration": "30m", "type": "prep"},
            {"time": "2:00 PM", "title": "Q4 Planning Meeting", "date": today_str, "duration": "60m", "type": "meeting"},
            {"time": "4:30 PM", "title": "Client Call — Follow-up", "date": today_str, "duration": "30m", "type": "call"},
        ]

    def _get_google_calendar_today(self) -> List[Dict[str, Any]]:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        service = build('calendar', 'v3', credentials=creds)

        now = datetime.utcnow()
        start = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'
        end = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId='primary',
            timeMin=start,
            timeMax=end,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        result = []
        for ev in events:
            start_time = ev['start'].get('dateTime', ev['start'].get('date'))
            try:
                dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                time_str = dt.strftime("%I:%M %p")
            except:
                time_str = start_time
            
            result.append({
                "time": time_str,
                "title": ev.get('summary', 'No title'),
                "date": datetime.now().date().isoformat(),
                "duration": "60m",
                "type": "meeting",
                "location": ev.get('location', ''),
                "description": ev.get('description', '')[:100]
            })
        
        return result

    def get_emails_unread(self) -> List[Dict[str, Any]]:
        """Get unread emails — real Gmail or local mock."""
        # Try real Gmail
        if self.is_authenticated():
            try:
                return self._get_gmail_unread()
            except Exception as e:
                print(f"Gmail failed: {e}, using local")

        # Local file
        if self.emails_path.exists():
            try:
                emails = json.loads(self.emails_path.read_text())
                unread = [e for e in emails if e.get("unread")]
                if unread:
                    return unread
            except:
                pass

        # Mock
        return [
            {"from": "client@example.com", "subject": "Need Q4 brief by Friday — Action Required", "time": "09:30", "unread": True, "important": True},
            {"from": "team@company.com", "subject": "Project update — on track", "time": "11:15", "unread": True, "important": False},
            {"from": "newsletter@example.com", "subject": "Weekly digest — 5 articles", "time": "14:00", "unread": False, "important": False},
        ]

    def _get_gmail_unread(self) -> List[Dict[str, Any]]:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
        creds = Credentials.from_authorized_user_file(str(self.token_path), SCOPES)
        service = build('gmail', 'v1', credentials=creds)

        results = service.users().messages().list(userId='me', q='is:unread', maxResults=10).execute()
        messages = results.get('messages', [])

        result = []
        for msg in messages[:10]:
            m = service.users().messages().get(userId='me', id=msg['id'], format='metadata', metadataHeaders=['From','Subject','Date']).execute()
            headers = {h['name']: h['value'] for h in m['payload'].get('headers', [])}
            
            result.append({
                "from": headers.get('From', 'Unknown')[:30],
                "subject": headers.get('Subject', 'No subject')[:50],
                "time": headers.get('Date', '')[:20],
                "unread": True,
                "important": 'important' in str(m.get('labelIds', [])).lower() or 'action' in headers.get('Subject','').lower()
            })
        
        return result

    def add_calendar_event(self, title: str, time_str: str = "", date_str: str = "") -> str:
        """Add event to local calendar.json."""
        date_str = date_str or datetime.now().date().isoformat()
        time_str = time_str or datetime.now().strftime("%I:%M %p")
        
        events = []
        if self.calendar_path.exists():
            try:
                events = json.loads(self.calendar_path.read_text())
            except:
                pass
        
        events.append({
            "time": time_str,
            "title": title,
            "date": date_str,
            "created": datetime.now().isoformat()
        })
        
        self.calendar_path.write_text(json.dumps(events[-100:], indent=2))
        return f"Added to calendar: {date_str} {time_str} — {title}"

    def add_email(self, from_addr: str, subject: str, unread: bool = True) -> str:
        """Add email to local emails.json."""
        emails = []
        if self.emails_path.exists():
            try:
                emails = json.loads(self.emails_path.read_text())
            except:
                pass
        
        emails.append({
            "from": from_addr,
            "subject": subject,
            "time": datetime.now().strftime("%H:%M"),
            "unread": unread,
            "important": any(k in subject.lower() for k in ["action", "urgent", "need", "required"]),
            "date": datetime.now().date().isoformat()
        })
        
        self.emails_path.write_text(json.dumps(emails[-100:], indent=2))
        return f"Added email: {from_addr} — {subject}"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Google Calendar + Gmail Setup")
    parser.add_argument("--setup", action="store_true", help="Run OAuth flow")
    parser.add_argument("--calendar", action="store_true", help="Show today's calendar")
    parser.add_argument("--emails", action="store_true", help="Show unread emails")
    parser.add_argument("--instructions", action="store_true", help="Show setup instructions")
    args = parser.parse_args()

    conn = GoogleConnector()
    
    if args.instructions:
        print(conn.setup_instructions())
    elif args.setup:
        print(conn.setup())
    elif args.calendar:
        print(json.dumps(conn.get_calendar_today(), indent=2))
    elif args.emails:
        print(json.dumps(conn.get_emails_unread(), indent=2))
    else:
        parser.print_help()
        print("\n" + conn.setup_instructions())
