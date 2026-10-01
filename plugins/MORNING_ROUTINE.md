# JARVIS morning command routine

A drop-in plugin suite. **No core file is modified** — everything lives in
`plugins/`, is discovered by the existing loader at startup, and can be removed
by deleting the files.

## What one run does

1. **Open or connect to JAUTOMATIC** — attaches to a running instance over its
   local HTTP API; launches the configured app if nothing answers; falls back to
   a labelled snapshot if it still can't connect, so the briefing is never blank.
2. **Job Search** using your saved profile.
3. **Queue** every job scoring **≥ 40 %** into the Applications queue. This is a
   *review list*. Nothing is ever submitted.
4. **Education** — works out which skills the shortlisted jobs demand that your
   profile lacks, weights them by how many jobs want them, and picks **one**
   course that closes the most. Reports the course and its **total duration**.
5. **ADHD-friendly day plan** — fixed short work blocks, a scheduled break after
   every one, a long break every fourth, protected lunch, hardest work first,
   one concrete action per block, nothing past your end time.
6. **Read-only briefings** — Gmail, Outlook, WhatsApp Business, market,
   Shilatech, JAUTOMATIC.

## Hard safety rules

JARVIS **never** submits an application, sends an email, sends a WhatsApp
message, deletes a message, or executes a trade.

This is enforced mechanically in `_jmorning_safety.py`, not by convention:

- `http_get()` is the suite's only network helper and refuses any method other
  than `GET`/`HEAD`. There is no `http_post` anywhere.
- `guard()` vetoes non-HTTP side effects by intent before the call is made, and
  every refusal is audited and printed in the run's safety line.
- The **one** permitted state change is `queue_jobs()` — hard-wired to the queue
  endpoint with `submit: false`, so it cannot be repurposed into an apply call.
- The test suite asserts all of the above, including a token-level scan proving
  no live `.Send()` / `.Delete()` / `.Reply()` call exists in the suite.

## Tools exposed

| Tool | Say | Does |
|---|---|---|
| `morning_routine` | "good morning", "run my morning briefing" | the full run above |
| `morning_report` | "read back the morning report", "what jobs did you queue" | replays the saved report / pending queue without re-running |

## Startup behaviour

Plugin discovery runs at JARVIS startup, so importing the module *is* the
startup hook. The routine self-schedules on a daemon thread after a short
delay, at most once per calendar day, and writes
`memory/morning_report_YYYY-MM-DD.md`. Turn it off with the **autorun** setting.

## Configuration

Settings → Plugins. Namespaces:

**`jarvis_morning`** — `autorun`, `day_end`, `block_minutes` (25),
`break_minutes` (5), `long_break_minutes` (20), `lunch_at`, `lunch_minutes`,
`min_score` (40), `max_course_blocks`, `max_job_blocks`.

**`jautomatic`** — `base_url` (default `http://127.0.0.1:8750`), `api_token`,
`app_path` (executable or URL to launch), `timeout`, `launch_timeout`.

**`outlook`** — reads your **existing desktop Outlook profile** over COM, so all
accounts already configured there (including Gmail) work with no extra OAuth.
`accounts` (`all` / `gmail` / comma-separated names), `gmail_accounts`,
`lookback_hours`, `max_items`. Windows-only; degrades gracefully elsewhere.

**`whatsapp`** — `access_token`, `phone_number_id`, `api_version`, `inbox_file`.
Note: Meta's Cloud API has no endpoint to *list* inbound messages — they arrive
on your webhook only. So this reads account health (quality rating, messaging
tier) over GET, plus an optional JSON inbox file your webhook writes.

**`market`** — `symbols`, `currency`, `api_url` (CoinGecko by default).

**`shilatech`** — `base_url`, `api_token`; falls back to
`memory/shilatech_snapshot.json`.

## Tests

```bash
python tests/test_morning_routine.py      # 45 tests, no pytest needed
```

Covers the safety rules, the 40 % cutoff (inclusive), score normalisation,
skill-gap ranking, single-course selection and duration reporting, plan
invariants (uniform short blocks, break after every block, no overlaps,
protected lunch, honours end time, carries overflow forward), all six
summaries, the end-to-end run, and the plugin loader contract — including an
assertion that no core file has been modified.
