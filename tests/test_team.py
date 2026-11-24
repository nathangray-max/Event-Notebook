import json

import pytest
import yaml

from confnotes import team

STAMP = {"commit": "abc1234", "date": "2025-03-06", "uncommitted_changes": False}
SESSION = "events/example-summit-2025/sessions/creatine-beyond-muscle"


def _confidential(store_root):
    p = store_root / SESSION / "session.yaml"
    d = yaml.safe_load(p.read_text()); d["confidential"] = True; d["format"] = "conversation"
    p.write_text(yaml.safe_dump(d, sort_keys=False))


def test_team_library_lists_summarised_public_sessions(fixture_copy, tmp_path):
    lib = team.write(tmp_path / "team", fixture_copy, stamp=STAMP, render=False)
    lessons = [l["id"] for c in lib["courses"] for l in c["lessons"]]
    assert "creatine-beyond-muscle" in lessons
    l = next(l for c in lib["courses"] for l in c["lessons"] if l["id"] == "creatine-beyond-muscle")
    assert l["summary"] and l["takeaways"] and l["level"] in {"Essential", "Recommended", "Background"}
    for internal in ("to_check", "notes", "transcript", "followups", "added_by"):
        assert internal not in l


def test_confidential_sessions_never_reach_the_team_library(fixture_copy, tmp_path):
    _confidential(fixture_copy)
    out = tmp_path / "team"
    team.write(out, fixture_copy, stamp=STAMP, render=False)
    text = (out / "data" / "library.json").read_text()
    assert "creatine-beyond-muscle" not in text
    lib = json.loads(text)
    assert all(l["id"] != "creatine-beyond-muscle" for c in lib["courses"] for l in c["lessons"])
    assert "creatine-beyond-muscle" not in json.dumps(lib["themes"])


def test_team_build_refuses_to_name_a_confidential_lead(fixture_copy, tmp_path):
    (fixture_copy / "leads.yaml").write_text(yaml.safe_dump({"leads": [{
        "id": "acme", "company": "Creatine beyond muscle (secret)", "kinds": ["acquisition"], "status": "heard",
        "confidential": True, "sources": [{"event": "example-summit-2025", "session": "clear-protein-panel"}],
        "summary": "x", "added": "2025-03-06"}]}))
    with pytest.raises(team.TeamLeak):
        team.write(tmp_path / "team", fixture_copy, stamp=STAMP, render=False)
    assert not (tmp_path / "team" / "data" / "library.json").exists()


def test_basic_themes_are_few_and_ordered():
    assert team.basic_themes(["longevity-positioning", "creatine-beyond-strength", "delivery-formats"]) == ["creatine-muscle", "healthy-ageing"]
    assert team.basic_themes(["ai-in-nutraceuticals"]) == ["evidence-claims"]
    assert team.basic_themes([]) == []
    assert len(team.BASIC_THEMES) <= 10
