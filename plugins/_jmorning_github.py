"""GET-only GitHub briefing for the Shilatech repository."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from plugins._jmorning_safety import http_get_json
from plugins._jmorning_sources import Summary, _cfg

def github_summary():
    repo = str(_cfg("shilatech_github", "repo", "eugenshila/shilatech"))
    token = _cfg("shilatech_github", "api_token", "")
    headers = {"Accept":"application/vnd.github+json", "User-Agent":"JARVIS morning briefing"}
    if token: headers["Authorization"] = f"Bearer {token}"
    base = f"https://api.github.com/repos/{repo}"
    try:
        pulls = http_get_json(base+"/pulls", params={"state":"open","per_page":20}, headers=headers)
        issues = http_get_json(base+"/issues", params={"state":"open","per_page":20}, headers=headers)
        since = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        commits = http_get_json(base+"/commits", params={"since":since,"per_page":20}, headers=headers)
        runs = http_get_json(base+"/actions/runs", params={"per_page":20}, headers=headers)
        failed = [r for r in runs.get("workflow_runs",[]) if r.get("conclusion") in ("failure","timed_out","cancelled")]
        real_issues = [i for i in issues if "pull_request" not in i]
        lines = [f"Open PRs: {len(pulls)}", f"Open issues: {len(real_issues)}", f"Commits since yesterday: {len(commits)}", f"Recent failing CI runs: {len(failed)}"]
        lines += [f"PR: {p.get('title','?')}" for p in pulls[:4]]
        return Summary("Shilatech GitHub", "repository briefing available.", lines, note="GET-only GitHub REST")
    except Exception as e:
        return Summary("Shilatech GitHub", "not reachable; no repository facts asserted.", degraded=True, note=str(e)[:90])
