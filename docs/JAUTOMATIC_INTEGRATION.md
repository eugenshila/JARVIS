# JAUTOMATIC Integration in JARVIS

JARVIS now integrates with `eugenshila/JAUTOMATIC-JOB-SEARCH` as the specialist Career OS engine.

## Architecture

```text
JARVIS      = HUD, voice, ADHD planning, daily command center
JAUTOMATIC  = job search, matching, CV/letters, tracker, training, interview prep
```

JARVIS does not duplicate JAUTOMATIC. It reads the local JAUTOMATIC workspace and turns it into daily plans, reminders, and HUD summaries.

## Does this need PostgreSQL?

No.

For the personal MSI build:

- JARVIS uses local config files and local stores.
- JAUTOMATIC uses `jautomatic.sqlite3` plus JSON profile/settings.
- The integration reads SQLite using Python's standard library.
- PostgreSQL is only a future option for team/multi-device/server deployments.

## Workspace detection

JARVIS checks:

- `JAUTOMATIC_DATA_DIR`
- Windows: `%APPDATA%\\JAUTOMATIC`
- Linux/macOS: `~/.local/share/jautomatic-job-search`

It also tries to find the app/source from:

- `JAUTOMATIC_APP_PATH`
- `JAUTOMATIC_REPO` (or `JAUTOMATIC_SOURCE` / `JAUTOMATIC_HOME`)
- common installed Windows path: `C:\\Program Files\\JAUTOMATIC\\jautomatic.exe`
- a sibling source checkout named either `JAUTOMATIC-JOB-SEARCH` or `JAUTOMATIC`, next to this repo, in `$HOME`, or one level above `$HOME` (e.g. `../JAUTOMATIC-JOB-SEARCH/main.py` or `../JAUTOMATIC/main.py`)

## Commands

```bash
jarvis career status
jarvis career today
jarvis career mode --set seeking
jarvis career mode --set employed
jarvis career mode --set open_to_better
jarvis career mode --set paused
jarvis career followups
jarvis career training
jarvis career open --yes
jarvis career paths
jarvis career postgres
```

## Career modes

### seeking
For active job search:

- follow-ups
- applications
- fresh job search
- free training
- interview prep

### employed
For after you get the job:

- log achievements
- upskill weekly
- maintain CV quietly
- prepare promotion/review evidence

### open_to_better
For employed but open:

- current job performance first
- passive strong-match review
- better-opportunity watchlist

### paused
For low-pressure maintenance:

- profile upkeep
- light training
- no aggressive search

## HUD

The circular HUD now has a Career OS card showing:

- current career mode
- jobs tracked
- applications tracked
- follow-ups due
- buttons for today's career plan and opening JAUTOMATIC

## Safety

JARVIS does not auto-submit applications, auto-login to job boards, or send emails. JAUTOMATIC prepares materials and drafts; the user reviews and sends/submits.
