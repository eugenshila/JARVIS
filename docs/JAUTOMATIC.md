# JAUTOMATIC integration

JARVIS exposes JAUTOMATIC JOB SEARCH as a native voice/tool action. It can read
and update JAUTOMATIC's shared local workspace and, on Windows, focus the
JAUTOMATIC desktop application and select any tab.

| Tab | Supported actions |
| --- | --- |
| Dashboard | `view`, `stats`, `refresh`, `navigate` |
| Profile | `view`, `update`, `navigate` |
| Job search | `search`, `list_jobs`, `move_to_applications`, `shortlist`, `prepare`, `open_job`, `navigate` |
| Tasks | `list`, `recommendations`, `add`, `update`, `open_task`, `set_status`, `navigate` |
| Education | `list_courses`, `details`, `open_course`, `start`, `complete`, `set_status`, `add_skills`, `reset_progress`, `navigate` |
| Applications / Sent / Archive | `list`, `add_matching`, `prepare`, `set_status`, `open_job`, `open_document`, `interview_prep`, follow-up actions, `navigate` |
| Insights | `view`, `analytics`, `refresh`, `navigate` |
| Settings | `view`, `update`, `export_csv`, `export_calendar`, `navigate` |

Data operations call JAUTOMATIC's headless service layer rather than clicking
form controls. This is more reliable and uses the same profile, settings,
SQLite database, course progress, paid tasks, and generated-document folders as
the desktop app. When `show=true`, JARVIS also focuses the Windows desktop app
and opens the affected tab. A plain `navigate` action only changes the visible
tab.

## Setup

The bridge needs the JAUTOMATIC **source checkout**, even when its Windows MSI is
already installed. Clone both repositories into the same parent directory:

```text
projects/
├── JARVIS/
└── JAUTOMATIC-JOB-SEARCH/
```

Alternatively, set the repository path explicitly in JARVIS's `.env`:

```env
JAUTOMATIC_PATH=C:/Users/you/Documents/GitHub/JAUTOMATIC-JOB-SEARCH
```

Install the JARVIS dependencies in JARVIS's environment. Its requirements
already include JAUTOMATIC's headless dependencies (`requests` and
`python-docx`) and Windows UI navigation dependency (`pywinauto`). PySide6 is
only needed to run JAUTOMATIC's source desktop interface; it is not needed when
the installed desktop application is used.

JAUTOMATIC resolves its workspace normally (`%APPDATA%\JAUTOMATIC` on Windows).
Set `JAUTOMATIC_DATA_DIR` to override it, or pass `data_dir` in an action for a
portable workspace.

## Job-search workflow

Search results and Applications are deliberately separate:

1. `search` fetches, scores, and saves results, returning a `job_id` for every
   result. It does not silently put every result in the application queue.
2. `move_to_applications` accepts `job_id`, `job_ids`, `count` (top matches), or
   `all_results=true`. Use `all_results` only when the user explicitly requests
   every result.
3. `prepare` accepts a `job_id` or `application_id` and generates the configured
   CV, cover letter, and email draft.
4. `open_job` opens the original posting; `open_document` opens a prepared CV,
   cover letter, email, or interview-prep file.

## Example requests

- “Open the JAUTOMATIC dashboard.”
- “Search JAUTOMATIC for remote logistics coordinator jobs in Kenya.”
- “Show the latest jobs, then move the top three to Applications.”
- “Move job `<job-id>` to Applications and open that tab.”
- “Prepare materials for application `<application-id>`.”
- “Open the CV for application `<application-id>`.”
- “Show courses under Education.”
- “Open the Power BI course and mark it in progress.”
- “Show my paid tasks.”
- “Show follow-ups due in JAUTOMATIC.”
- “Export my application tracker to CSV.”

Application-changing operations use the IDs returned by Search or Applications.
JARVIS does not submit applications automatically; JAUTOMATIC retains its
review-and-submit safety boundary.

## Direct diagnostic

From the JARVIS project directory on Windows PowerShell:

```powershell
$env:JAUTOMATIC_PATH = "C:\Users\you\Documents\GitHub\JAUTOMATIC-JOB-SEARCH"
.\.venv\Scripts\python.exe -c "from actions.jautomatic import jautomatic_action; print(jautomatic_action({'tab':'education','action':'list_courses'}))"
```

This should print the course catalog without requiring the JAUTOMATIC window to
be open.
