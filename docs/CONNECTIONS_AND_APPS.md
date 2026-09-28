# JARVIS Pre-MSI Connected Features

These are the safety checks added before treating the MSI as a daily connected assistant.

## 1. ADHD support state, not diagnosis

JARVIS does **not** determine a medical ADHD severity level. It asks for daily operating signals and converts them into a support mode:

- Energy 1-10
- Focus 1-10
- Stress/overwhelm 1-10
- Sleep hours
- Mood words
- Optional medication state: unknown, not applicable, taken, skipped

Run:

```bash
jarvis adhd-state --energy 5 --focus 6 --stress 4 --sleep-hours 7 --mood calm
jarvis adhd-state --status
```

Possible modes:

- Low Battery
- Wired but Tired
- Buzzing / Restless
- Hyperfocus Risk
- Scattered Guardrails
- Overwhelm SOS
- Steady

The score is an operational **support load**, not a diagnosis.

## 2. Calendar and email

### Google Calendar/Gmail

Google is available through OAuth and is read-only by default.

```bash
jarvis connect status
jarvis connect google --instructions
jarvis connect google --setup
```

OAuth files stay local:

- `~/.jarvis/google_credentials.json`
- `~/.jarvis/google_token.json`

Once authenticated, the enhanced calendar and email tools use real Google Calendar/Gmail for morning briefings.

### Microsoft Outlook/Office 365

Microsoft setup guidance is available:

```bash
jarvis connect microsoft --instructions
```

The intended connector is Microsoft Graph OAuth with read-only scopes first:

- `Calendars.Read`
- `Mail.Read`
- `User.Read`

### Local fallback

Offline/manual files:

```bash
jarvis connect local
```

- `~/.jarvis/calendar.json`
- `~/.jarvis/emails.json`

## 3. Installed software launcher

JARVIS can open installed software only through a local allow-list. It will not run arbitrary shell commands from chat.

```bash
jarvis apps --discover
jarvis apps --list
jarvis apps --add --name Outlook --path "C:\\Program Files\\Microsoft Office\\root\\Office16\\OUTLOOK.EXE"
jarvis apps --launch Outlook --yes
```

Safety rules:

- Launch requires explicit confirmation.
- Scripts such as `.bat`, `.cmd`, `.ps1`, `.vbs`, `.js`, and `.jar` are blocked.
- App paths are stored locally in `~/.jarvis/apps.json`.
- Command-line arguments are disabled unless an app is explicitly added with `--allow-args`.

## 4. Career OS / JAUTOMATIC

JARVIS integrates with `eugenshila/JAUTOMATIC-JOB-SEARCH` for job hunting, free training, follow-ups, CV/letter materials, and interview prep.

Commands:

```bash
jarvis career status
jarvis career today
jarvis career mode --set seeking
jarvis career mode --set employed
jarvis career followups
jarvis career training
jarvis career open --yes
jarvis career postgres
```

PostgreSQL is not required. JAUTOMATIC uses local SQLite (`jautomatic.sqlite3`) and JSON files.

## 5. HUD readiness screen

The circular HUD now surfaces:

- ADHD daily support-state check
- Google/Microsoft/local connection status
- Career OS / JAUTOMATIC stats and mode
- Approved app launcher buttons

Backend endpoints:

- `GET /hud/preflight`
- `POST /hud/adhd-state`
- `GET /hud/connections`
- `POST /hud/connections/google/setup`
- `GET /hud/apps`
- `POST /hud/apps`
- `POST /hud/apps/launch`
- `GET /hud/career`
- `GET /hud/career/today`
- `POST /hud/career/mode`
- `POST /hud/career/open`

All connection, app, and career actions are local-first and permission-based.
