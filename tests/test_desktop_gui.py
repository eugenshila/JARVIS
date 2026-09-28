from pathlib import Path


def test_find_frontend_requires_index_and_assets(monkeypatch, tmp_path: Path):
    from jarvis.cli import desktop_gui

    incomplete = tmp_path / "incomplete"
    incomplete.mkdir()
    (incomplete / "index.html").write_text("missing assets", encoding="utf-8")

    complete = tmp_path / "complete"
    (complete / "assets").mkdir(parents=True)
    (complete / "index.html").write_text("<!doctype html>", encoding="utf-8")

    monkeypatch.setattr(desktop_gui, "frontend_candidates", lambda: [incomplete, complete])
    assert desktop_gui.find_frontend() == complete


def test_find_frontend_error_explains_how_to_build(monkeypatch, tmp_path: Path):
    import pytest
    from jarvis.cli import desktop_gui

    monkeypatch.setattr(desktop_gui, "frontend_candidates", lambda: [tmp_path / "missing"])
    with pytest.raises(FileNotFoundError, match=r"npm ci && npm run build"):
        desktop_gui.find_frontend()
