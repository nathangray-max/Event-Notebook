"""store.py: the fixture is clean, every check fires on the right fault, the real store is clean."""
from pathlib import Path

import yaml

from confnotes import store
from tests.conftest import FIXTURE

EV = "events/example-summit-2025"
SESS = EV + "/sessions/creatine-beyond-muscle"


def _edit_yaml(path: Path, **changes):
    d = yaml.safe_load(path.read_text())
    d.update(changes)
    path.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))


def test_fixture_is_clean_and_loads():
    assert store.problems(FIXTURE) == []
    st = store.load(FIXTURE)
    assert [e["id"] for e in st["events"]] == ["example-summit-2025"]
    e = st["events"][0]
    assert [s["id"] for s in e["sessions"]] == ["clear-protein-panel", "creatine-beyond-muscle"]  # folder order; the build sorts by time
    s = [x for x in e["sessions"] if x["id"] == "creatine-beyond-muscle"][0]
    assert "[12:40]" in s["transcript"] and s["notes"].startswith("Nathan's notes")
    assert [h for h in list(s["summary"])[1:] if h in store.SUMMARY_HEADINGS] == store.SUMMARY_HEADINGS
    assert "Key slides" in s["summary"] and "Detail" in s["summary"]
    assert [f["name"] for f in s["files"]] == ["deck.pptx", "handout.pdf", "photo-01.webp"]
    assert store.photo_index(s["files"]) == {1: "photo-01.webp"}
    assert s["files"][0]["pages"] == 3 and "[notes]" in s["files"][0]["text"]
    assert s["files"][1]["pages"] == 2 and "Handout page two" in s["files"][1]["text"]
    assert list(e["report"])[1:] == store.REPORT_HEADINGS
    assert e["themes"][0]["theme"] == "creatine-beyond-muscle"


def test_real_store_is_clean():
    assert store.problems() == []


def test_sections_and_bullets():
    md = "# T\nintro\n## A\n- one\n  continued\n- two\n## B\ntext"
    sec = store.split_sections(md)
    assert sec[""] == "# T\nintro" and sec["B"] == "text"
    assert store.bullets(sec["A"]) == ["one continued", "two"]


def test_summary_line():
    assert store.summary(store.load(FIXTURE)) == (
        "1 events (1 reported), 2 sessions (1 captured, 0 summarised, 1 reviewed), 3 files, 1 transcripts, 3 themes, 1 things to check")


def test_unknown_theme_and_bad_values(fixture_copy):
    p = fixture_copy / SESS / "session.yaml"
    _edit_yaml(p, themes=["not-a-theme"], format="lecture", relevance="vital", date="4 March", start="9.30")
    probs = store.problems(fixture_copy)
    assert any("theme 'not-a-theme' is not in data/themes.yaml" in x for x in probs)
    assert any("format 'lecture' not in" in x for x in probs)
    assert any("relevance 'vital' not in" in x for x in probs)
    assert any("date '4 March' is not YYYY-MM-DD" in x for x in probs)
    assert any("start '9.30' is not HH:MM" in x for x in probs)


def test_status_rules(fixture_copy):
    p = fixture_copy / SESS / "session.yaml"
    # reviewed without a reviewer
    _edit_yaml(p, reviewed_by="", reviewed_date="")
    assert any("reviewed needs reviewed_by and reviewed_date" in x for x in store.problems(fixture_copy))
    # a summary exists but the status says captured
    _edit_yaml(p, status="captured", reviewed_by="", reviewed_date="")
    assert any("has a summary but status is 'captured'" in x for x in store.problems(fixture_copy))
    # summarised but nothing to summarise from
    other = fixture_copy / EV / "sessions/clear-protein-panel"
    (other / "notes.md").unlink()
    _edit_yaml(other / "session.yaml", status="summarised")
    probs = store.problems(fixture_copy)
    assert any("no transcript, notes or files to summarise from" in x for x in probs)
    assert any("status 'summarised' but no summary.md" in x for x in probs)


def test_summary_headings_and_title(fixture_copy):
    p = fixture_copy / SESS / "summary.md"
    p.write_text(p.read_text().replace("## Quotes", "## Quotations"))
    assert any("missing headings ['Quotes']" in x for x in store.problems(fixture_copy))
    p.write_text("no title\n" + p.read_text())
    assert any("must start with '# <title>'" in x for x in store.problems(fixture_copy))


def test_event_rules(fixture_copy):
    ev = fixture_copy / EV
    th = ev / "themes.yaml"
    d = yaml.safe_load(th.read_text())
    d["themes"][0]["evidence"][0]["session"] = "no-such-session"
    d["themes"].append({"theme": "creatine-beyond-muscle", "headline": "twice", "strength": "huge", "evidence": [{"session": "clear-protein-panel"}]})
    th.write_text(yaml.safe_dump(d))
    probs = store.problems(fixture_copy)
    assert any("names session 'no-such-session'" in x for x in probs)
    assert any("listed twice" in x for x in probs)
    assert any("strength 'huge' not in" in x for x in probs)
    assert any("has no quote" in x for x in probs)
    # report present but status not reported; report missing a heading
    _edit_yaml(ev / "event.yaml", status="attended", start="2025-03-06", end="2025-03-05")
    r = ev / "report.md"
    r.write_text(r.read_text().replace("## Sources", "## Where it came from"))
    probs = store.problems(fixture_copy)
    assert any("has a report but status is 'attended'" in x for x in probs)
    assert any("missing headings ['Sources']" in x for x in probs)
    assert any("end before start" in x for x in probs)


def test_ids_match_folders(fixture_copy):
    _edit_yaml(fixture_copy / SESS / "session.yaml", id="Creatine Beyond")
    probs = store.problems(fixture_copy)
    assert any("differs from its folder name" in x for x in probs)
    assert any("lower-case words joined by hyphens" in x for x in probs)
    _edit_yaml(fixture_copy / EV / "event.yaml", id="other-2025")
    assert any("id 'other-2025' differs from its folder name" in x for x in store.problems(fixture_copy))


def test_unquoted_colon_in_a_list(fixture_copy):
    p = fixture_copy / SESS / "session.yaml"
    p.write_text(p.read_text().replace("ingredients: [CreaWin, creatine monohydrate]", "ingredients: [CreaWin, IsoClr: Pea]"))
    assert any("ingredients must be a list of strings" in x for x in store.problems(fixture_copy))


def test_duplicate_theme_id(fixture_copy):
    th = fixture_copy / "themes.yaml"
    d = yaml.safe_load(th.read_text())
    d["themes"].append(dict(d["themes"][0]))
    th.write_text(yaml.safe_dump(d))
    assert any("duplicate id" in x for x in store.problems(fixture_copy))


def test_broken_yaml_is_one_problem(fixture_copy):
    (fixture_copy / EV / "event.yaml").write_text("id: [unclosed")
    probs = store.problems(fixture_copy)
    assert len(probs) == 1 and probs[0].startswith("cannot load")


def test_summary_format(fixture_copy):
    p = fixture_copy / SESS / "summary.md"
    base = p.read_text()
    # a Summary that is a list of cited figures, not prose
    p.write_text(base.replace("not for lifting.", "not for lifting [12:40]. " + "word " * 230))
    probs = store.problems(fixture_copy)
    assert any("Summary carries cites" in x for x in probs)
    assert any("keep it under 220" in x for x in probs)
    # too many takeaways
    p.write_text(base.replace("## Key slides", "- a\n- b\n- c\n\n## Key slides"))
    assert any("7 key takeaways" in x for x in store.problems(fixture_copy))
    # a key slide that is not one of the session's photos, and one without a photo number
    p.write_text(base.replace("- (photo 1) The 2024 trial", "- (photo 9) A slide we do not have\n- The 2024 trial"))
    probs = store.problems(fixture_copy)
    assert any("key slide photo 9 is not among" in x for x in probs)
    assert any("must start '(photo N)'" in x for x in probs)
    # Key slides and Detail are optional
    p.write_text(base.split("## Key slides")[0] + "## For Vita Actives" + base.split("## For Vita Actives")[1].split("## Detail")[0] + "## Follow-ups" + base.split("## Follow-ups")[1])
    assert store.problems(fixture_copy) == []
