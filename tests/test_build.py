"""build.py: records, cites, theme aggregation, the stamp, refusal on problems."""
import json

import pytest

from confnotes import build, store
from tests.conftest import FIXTURE

STAMP = {"commit": "abc1234", "date": "2025-03-06", "uncommitted_changes": False}


def test_cites():
    assert build.cites("older buyer [12:40] and (slide 7), from the room (notes); long [1:02:10]") == ["12:40", "slide 7", "notes", "1:02:10"]
    assert build.cites("a reading") == []


def test_fixture_build(tmp_path):
    out = tmp_path / "events.json"
    d = build.build(out, FIXTURE, stamp=STAMP)
    assert d["generated"] == STAMP
    e = d["events"][0]
    assert e["id"] == "example-summit-2025" and e["has_report"]
    assert e["report"]["In brief"].startswith("- Creatine was sold")
    assert [s["id"] for s in e["sessions"]] == ["creatine-beyond-muscle", "clear-protein-panel"]  # by date and time
    s = e["sessions"][0]
    assert s["event"] == "example-summit-2025"
    assert [t["cites"] for t in s["takeaways"]] == [["12:40"], ["18:05"], ["slide 3"], []]
    assert s["quotes"][0]["text"].startswith('"The strength story is told.')
    assert s["followups"] == ["Ask Dr Example for the 2024 trial paper (notes)."]
    assert s["has_transcript"] and s["transcript_words"] > 20 and s["has_notes"] and s["has_summary"]
    assert "summary_md" not in s and "_path" not in s
    assert s["files"][0]["pages"] == 3 and "--- slide 3 ---" in s["files"][0]["text"]
    c = e["sessions"][1]
    assert not c["has_summary"] and c["takeaways"] == [] and c["summary"]["Summary"] == ""
    themes = {t["id"]: t for t in d["themes"]}
    assert themes["creatine-beyond-muscle"]["events"][0]["headline"].startswith("Two of five talks")
    assert themes["creatine-beyond-muscle"]["sessions"] == [{"event": "example-summit-2025", "session": "creatine-beyond-muscle", "title": "Creatine beyond muscle", "date": "2025-03-04"}]
    assert themes["unused-theme"]["events"] == [] and themes["unused-theme"]["sessions"] == []
    assert json.loads(out.read_text())["events"][0]["id"] == "example-summit-2025"


def test_dates_are_strings(tmp_path):
    d = build.build(tmp_path / "e.json", FIXTURE, stamp=STAMP)
    s = d["events"][0]["sessions"][0]
    assert s["date"] == "2025-03-04" and s["start"] == "09:30" and d["events"][0]["start"] == "2025-03-04"


def test_refuses_on_problems(fixture_copy, tmp_path):
    (fixture_copy / "events/example-summit-2025/sessions/creatine-beyond-muscle/summary.md").write_text("# T\n## Summary\nonly")
    out = tmp_path / "e.json"
    with pytest.raises(build.StoreProblems):
        build.build(out, fixture_copy, stamp=STAMP)
    assert not out.exists()


def test_real_store_builds(tmp_path):
    d = build.build(tmp_path / "e.json")
    assert len(d["events"]) == len(store.load()["events"])
    assert d["generated"]["commit"] and d["generated"]["date"]
