import json
import sqlite3
from pathlib import Path


def _make_workspace(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    (root / "profile.json").write_text(json.dumps({
        "name": "Eugene",
        "headline": "IT Support / AI Automation",
        "desired_titles": ["IT Support", "Junior Developer"],
        "skills": ["Python", "Windows", "Customer Support"],
        "extra": {
            "education_progress": {
                "ms-learn": {"status": "In progress"},
                "freecodecamp": {"status": "Completed"},
            }
        },
    }), encoding="utf-8")
    db = root / "jautomatic.sqlite3"
    conn = sqlite3.connect(db)
    conn.executescript(
        """
        CREATE TABLE jobs (
            job_id TEXT PRIMARY KEY,
            fingerprint TEXT,
            source TEXT,
            title TEXT,
            company TEXT,
            location TEXT,
            remote INTEGER DEFAULT 0,
            salary_min INTEGER DEFAULT 0,
            salary_max INTEGER DEFAULT 0,
            currency TEXT DEFAULT '',
            url TEXT DEFAULT '',
            description TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            posted_at TEXT DEFAULT '',
            fetched_at TEXT DEFAULT ''
        );
        CREATE TABLE applications (
            application_id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL,
            status TEXT DEFAULT 'discovered',
            match_score INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            sent_at TEXT DEFAULT '',
            follow_up_at TEXT DEFAULT '',
            interview_at TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            cv_path TEXT DEFAULT '',
            cover_letter_path TEXT DEFAULT '',
            email_path TEXT DEFAULT '',
            history TEXT DEFAULT '[]',
            prep TEXT DEFAULT '{}',
            prep_path TEXT DEFAULT '',
            follow_up_count INTEGER DEFAULT 0
        );
        """
    )
    conn.execute("INSERT INTO jobs(job_id, title, company, location, remote, url, fetched_at) VALUES(?,?,?,?,?,?,?)",
                 ("job-1", "IT Support Analyst", "Acme", "Nairobi", 0, "https://example.com", "2026-09-28"))
    conn.execute("INSERT INTO applications(application_id, job_id, status, match_score, created_at, updated_at, sent_at, follow_up_at) VALUES(?,?,?,?,?,?,?,?)",
                 ("app-1", "job-1", "sent", 87, "2026-09-20", "2026-09-21", "2026-09-21", "2026-09-22"))
    conn.commit()
    conn.close()


def test_jautomatic_connector_reads_sqlite_without_postgres(monkeypatch, tmp_path):
    _make_workspace(tmp_path)
    monkeypatch.setenv("JAUTOMATIC_DATA_DIR", str(tmp_path))
    from jarvis.connectors.jautomatic import JAutomaticConnector

    stats = JAutomaticConnector().stats()
    assert stats["postgres_required"] is False
    assert stats["storage"] == "SQLite + JSON files"
    assert stats["jobs"] == 1
    assert stats["applications"] == 1
    assert stats["sent"] == 1
    assert stats["follow_ups_due"] == 1
    assert stats["training"]["in_progress"] == 1
    assert stats["training"]["completed"] == 1
    assert stats["top_matches"][0]["company"] == "Acme"


def test_career_tool_modes_and_today(monkeypatch, tmp_path):
    _make_workspace(tmp_path / "jautomatic")
    monkeypatch.setenv("JAUTOMATIC_DATA_DIR", str(tmp_path / "jautomatic"))
    monkeypatch.setenv("JARVIS_HOME", str(tmp_path / "jarvis"))
    from jarvis.tools.career_tools import CareerTool

    tool = CareerTool()
    assert "PostgreSQL" in tool.run(action="postgres")
    assert "Career mode set" in tool.run(action="mode", mode="employed")
    today = tool.run(action="today")
    assert "Employed" in today or "employed" in today
    assert "achievement" in today.lower()
