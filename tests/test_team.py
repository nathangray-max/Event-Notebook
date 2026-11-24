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
    assert "creatine-beyond-muscle" not in json.dumps(lib["facets"])


def test_team_build_refuses_to_name_a_confidential_lead(fixture_copy, tmp_path):
    (fixture_copy / "leads.yaml").write_text(yaml.safe_dump({"leads": [{
        "id": "acme", "company": "Creatine beyond muscle (secret)", "kinds": ["acquisition"], "status": "heard",
        "confidential": True, "sources": [{"event": "example-summit-2025", "session": "clear-protein-panel"}],
        "summary": "x", "added": "2025-03-06"}]}))
    with pytest.raises(team.TeamLeak):
        team.write(tmp_path / "team", fixture_copy, stamp=STAMP, render=False)
    assert not (tmp_path / "team" / "data" / "library.json").exists()


def test_facets_group_lessons_by_ingredient_category_and_tag(fixture_copy, tmp_path):
    (fixture_copy / "facets.yaml").write_text(yaml.safe_dump({
        "ingredients": [{"id": "creatine", "name": "Creatine", "match": ["creatine", "creawin"]}],
        "categories": [{"id": "sports", "name": "Sports performance"}],
        "tags": [{"id": "science", "name": "Science and evidence"}]}))
    p = fixture_copy / SESSION / "session.yaml"
    d = yaml.safe_load(p.read_text()); d["categories"] = ["sports"]; d["tags"] = ["science"]; d["ingredients"] = ["CreaWin"]
    p.write_text(yaml.safe_dump(d, sort_keys=False))
    lib = team.write(tmp_path / "team", fixture_copy, stamp=STAMP, render=False)
    key = "example-summit-2025--creatine-beyond-muscle"
    assert [f["lessons"] for f in lib["facets"]["ingredients"]] == [[key]]
    assert lib["facets"]["categories"][0]["name"] == "Sports performance" and lib["facets"]["tags"][0]["lessons"] == [key]


def test_person_ids():
    assert team.person_id({"name": "Martina Pavlová", "organisation": "FAVEA a.s."}) == "martina-pavlova"
    assert team.person_id({"name": "Dr. Ralf Spreemann", "organisation": "MartinBauer"}) == "ralf-spreemann"
    assert team.person_id({"name": "Nicholas Morgan"}) == team.person_id({"name": "Nick Morgan"}) == "nick-morgan"
    assert team.person_id({"name": "Miguel", "organisation": "Nuritas"}) != team.person_id({"name": "Miguel (surname unconfirmed)", "organisation": "SPI Pharma"})
    assert team.person_id({"name": "Kane", "organisation": "consumer panellist"}) == ""


def test_leak_check_ignores_image_data_but_catches_words():
    from confnotes.team import _leaks
    img = '"thumb": "data:image/webp;base64,QWxhbmFAIDPw3C9L/0SOVdmf+Y4="'
    assert _leaks(["AIDP"], img) == []
    assert _leaks(["AIDP"], img + ' "summary": "Talks with AIDP went well"') == ["AIDP"]
    assert _leaks(["AIDP"], '"summary": "paid partnerships"') == []
