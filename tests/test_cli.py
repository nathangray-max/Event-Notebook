"""__main__.py: new-event and new-session scaffold clean records; check exits 0 on the real store."""
import subprocess
import sys

import yaml

from confnotes import ROOT, __main__ as cli, store


def test_check_runs():
    r = subprocess.run([sys.executable, "-m", "confnotes", "check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "events" in r.stdout


def test_new_event_and_session(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "DATA", tmp_path)
    (tmp_path / "themes.yaml").write_text("themes: []\n")
    assert cli.main(["new-event", "test-summit-2026", "--name", "Test Summit 2026", "--start", "2026-05-01", "--city", "Leeds"]) == 0
    assert cli.main(["new-session", "test-summit-2026", "opening-keynote", "--title", "Opening keynote", "--date", "2026-05-01", "--format", "keynote"]) == 0
    e = yaml.safe_load((tmp_path / "events/test-summit-2026/event.yaml").read_text())
    assert e["id"] == "test-summit-2026" and e["end"] == "2026-05-01" and e["status"] == "attending"
    s = yaml.safe_load((tmp_path / "events/test-summit-2026/sessions/opening-keynote/session.yaml").read_text())
    assert s["status"] == "captured" and s["format"] == "keynote" and s["to_check"]
    assert (tmp_path / "events/test-summit-2026/sessions/opening-keynote/files").is_dir()
    assert store.problems(tmp_path) == []
    # refuses to overwrite
    assert cli.main(["new-event", "test-summit-2026", "--name", "again"]) == 1
    assert cli.main(["new-session", "test-summit-2026", "opening-keynote", "--title", "again"]) == 1
    assert cli.main(["new-session", "no-event-2026", "x", "--title", "x"]) == 1


def test_publish_files_lists_every_photo(capsys):
    import json
    assert cli.main(["publish-files"]) == 0
    m = json.loads(capsys.readouterr().out)
    for k, v in m.items():
        assert k.startswith("slides/") and k.endswith(".webp") and v.endswith(k.split("/")[-1])
        assert (ROOT / v).exists()
