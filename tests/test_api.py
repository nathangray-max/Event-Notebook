"""api.py: the contracts, their schemas, what stays out, the manifest."""
import json

from confnotes import api
from tests.conftest import FIXTURE

STAMP = {"commit": "abc1234", "date": "2025-03-06", "uncommitted_changes": False}


def test_contracts(tmp_path):
    out = tmp_path / "v1"
    m = api.write(out, FIXTURE, stamp=STAMP)
    assert m["schema"] == "confnotes.manifest/1" and m["commit"] == "abc1234"
    assert set(m["contracts"]) == {"events.json", "sessions.json", "themes.json", "takeaways.json"}
    assert not (out / ".events.tmp.json").exists()
    ev = json.loads((out / "events.json").read_text())
    assert ev["schema"] == "confnotes.events/1" and ev["count"] == 1
    e = ev["items"][0]
    assert e["sessions"] == ["creatine-beyond-muscle", "clear-protein-panel"]
    assert e["report"]["In brief"] and e["themes"][0]["theme"] == "creatine-beyond-muscle"
    se = json.loads((out / "sessions.json").read_text())
    s = se["items"][0]
    assert s["event"] == "example-summit-2025" and s["speakers"][0]["name"] == "Dr A. Example"
    assert "transcript" not in s and s["has_transcript"] and s["transcript_words"] > 0
    assert s["files"] == [{"name": "deck.pptx", "kind": "pptx", "pages": 3}, {"name": "handout.pdf", "kind": "pdf", "pages": 2},
                          {"name": "photo-01.webp", "kind": "photo", "pages": 1}]
    assert s["key_slides"][0]["file"] == "photo-01.webp" and len(s["detail"]) == 2
    assert s["summary"]["Key takeaways"] and se["items"][1]["summary"] is None
    tk = json.loads((out / "takeaways.json").read_text())
    assert tk["count"] == 4
    assert tk["items"][0] == {"id": "example-summit-2025/creatine-beyond-muscle#1", "event": "example-summit-2025", "session": "creatine-beyond-muscle",
                              "date": "2025-03-04", "text": "The next creatine buyer is older and buying for memory, not strength [12:40].",
                              "cites": ["12:40"], "themes": ["creatine-beyond-muscle"], "ingredients": ["CreaWin", "creatine monohydrate"],
                              "relevance": "high", "status": "reviewed"}
    assert tk["items"][3]["cites"] == []  # a reading
    th = json.loads((out / "themes.json").read_text())
    assert th["count"] == 3 and th["items"][0]["events"][0]["evidence"][0]["quote"].startswith("The strength story")
    for name, c in m["contracts"].items():
        import hashlib
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == c["sha256"]


def test_real_store_exports(tmp_path):
    m = api.write(tmp_path / "v1")
    assert m["contracts"]["events.json"]["count"] >= 1
