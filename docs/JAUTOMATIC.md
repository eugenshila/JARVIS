# JAUTOMATIC integration

JARVIS exposes JAUTOMATIC JOB SEARCH as a native voice/tool action. Operations follow the same tabs as the JAUTOMATIC desktop app:

| Tab | Supported actions |
| --- | --- |
| Dashboard | `view`, `stats`, `refresh` |
| Profile | `view`, `update` |
| Education | `view` |
| Search | `search` |
| Applications / Sent / Archive | `list`, `prepare`, `set_status`, `interview_prep` |
| Tasks | `list`, `draft_follow_up`, `postpone` |
| Insights | `view`, `analytics` |
| Settings | `view`, `update`, `export_csv`, `export_calendar` |

The integration calls JAUTOMATIC's headless service layer, so it does not open or automate the PySide interface. It uses the same profile, settings, SQLite database, and generated-document folders as the desktop app.

## Setup

Clone both repositories into the same parent directory:

```text
projects/
├── JARVIS/
└── JAUTOMATIC-JOB-SEARCH/
```

Alternatively, set the repository path explicitly:

```bash
export JAUTOMATIC_PATH=/path/to/JAUTOMATIC-JOB-SEARCH
```

Install the dependencies from both repositories into JARVIS's Python environment. JARVIS already includes JAUTOMATIC's headless runtime dependencies (`requests` and `python-docx`). PySide6 is only necessary when launching JAUTOMATIC's own desktop interface.

JAUTOMATIC continues to resolve its workspace normally. Set `JAUTOMATIC_DATA_DIR` to override it, or pass `data_dir` in an action for a portable workspace.

## Example requests

- “Show my JAUTOMATIC dashboard.”
- “Search JAUTOMATIC for remote logistics coordinator jobs in Kenya.”
- “List my prepared applications.”
- “Prepare the application pack for application `<id>`.”
- “Show follow-ups due in JAUTOMATIC.”
- “Export my application tracker to CSV.”

Application-changing operations require the application ID returned by a Search or Applications action. JARVIS does not submit applications automatically; JAUTOMATIC retains its review-and-submit safety boundary.
