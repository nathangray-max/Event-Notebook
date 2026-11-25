"""The training library (docs/training.md): the checks on the invented fixture (tests/fixture/training), the library's
shape, links to and from the team library by shared tags, and the plain-text fallback while a library has no address."""
import json

import pytest
import yaml

from confnotes import team, training

STAMP = {"commit": "abc1234", "date": "2026-11-25", "uncommitted_changes": False}
FACETS = {
    "ingredients": [{"id": "creatine", "name": "Creatine", "match": ["creatine"]},
                    {"id": "botanicals", "name": "Adaptogens and botanicals", "match": ["ashwagandha"]}],
    "categories": [{"id": "sports", "name": "Sports performance"}],
    "tags": [{"id": "science", "name": "Science and evidence"}, {"id": "market-data", "name": "Market and consumer data"}]}
MOD = "training/foundations/modules/creatine-basics"
TALK = "events/example-summit-2025/sessions/creatine-beyond-muscle/session.yaml"


@pytest.fixture
def store(fixture_copy):
    (fixture_copy / "facets.yaml").write_text(yaml.safe_dump(FACETS))
    p = fixture_copy / TALK
    d = yaml.safe_load(p.read_text()); d["categories"] = ["sports"]; d["tags"] = ["science"]
    p.write_text(yaml.safe_dump(d, sort_keys=False))
    return fixture_copy


def _edit_module(store, **kw):
    p = store / MOD / "module.yaml"
    d = yaml.safe_load(p.read_text()); d.update(kw)
    p.write_text(yaml.safe_dump(d, sort_keys=False))


def _edit_summary(store, old, new):
    p = store / MOD / "summary.md"
    t = p.read_text(); assert old in t
    p.write_text(t.replace(old, new))


def _build(store, tmp_path, sites=None):
    if sites is not None:
        (store / "sites.yaml").write_text(yaml.safe_dump(sites))
    team.write(tmp_path / "team", store, stamp=STAMP, render=False)
    lib = training.write(tmp_path / "training", store, stamp=STAMP)
    tlib = team.write(tmp_path / "team", store, stamp=STAMP, render=False)  # again, now that the training library exists
    return lib, tlib


def test_fixture_is_clean(store):
    assert training.problems(store) == []


@pytest.mark.parametrize("edit,expect", [
    (lambda s: _edit_module(s, level="urgent"), "level 'urgent'"),
    (lambda s: _edit_module(s, minutes="five"), "minutes must be a whole number"),
    (lambda s: _edit_module(s, tags=["gossip"]), "tag 'gossip' is not in data/facets.yaml"),
    (lambda s: _edit_module(s, categories=["space"]), "category 'space'"),
    (lambda s: _edit_module(s, deck="missing.pdf"), "deck 'missing.pdf' is not in files/"),
    (lambda s: _edit_module(s, status="reviewed"), "reviewed_by is blank"),
    (lambda s: _edit_module(s, course="markets"), "course 'markets' must be 'foundations'"),
    (lambda s: _edit_summary(s, "in plain prose with no cites.", "in plain prose (slide 1)."), "Summary carries cites"),
    (lambda s: _edit_summary(s, "in plain prose with no cites.", "word " * 220), "Summary is"),
    (lambda s: _edit_summary(s, "(slide 2).\n- The last", "(slide 9).\n- The last"), "cites slide 9 but the deck has 4 pages"),
    (lambda s: _edit_summary(s, "from the opening slide (slide 1).\n", "from the opening slide.\n"), "key learning 1 has no (slide N) cite"),
    (lambda s: _edit_summary(s, "- The last invented point (slide 4).\n", "".join(f"- Point {i} (slide 1).\n" for i in range(5))), "key learnings; keep at most 6"),
    (lambda s: _edit_summary(s, "(my reading)", ""), "In practice item 2"),
    (lambda s: _edit_summary(s, "  A: On the second slide (slide 2).", "  A: On the second slide."), "answer 2 has no (slide N) cite"),
    (lambda s: _edit_summary(s, "- Q: What closes the deck?\n  A: The last invented point (slide 4).\n", ""), "has 2 questions"),
    (lambda s: _edit_summary(s, "## In practice", "## Detail first\n\n## In practice"), "unknown heading 'Detail first'"),
    (lambda s: _edit_summary(s, "a figure the deck gives", "a whey figure"), "names whey"),
    (lambda s: _edit_summary(s, "when a customer asks", "when a.person@example.com asks"), "email address or phone number"),
])
def test_problems_catch_each_rule(store, edit, expect):
    edit(store)
    probs = training.problems(store)
    assert any(expect in p for p in probs), probs


def test_sections_out_of_order(store):
    p = store / MOD / "summary.md"
    t = p.read_text()
    a, b = t.index("## Key learnings"), t.index("## In practice")
    p.write_text(t[:a] + t[b:t.index("## Check")] + t[a:b] + t[t.index("## Check"):])
    assert any("out of order" in x for x in training.problems(store))


def test_build_refuses_with_problems(store, tmp_path):
    _edit_module(store, level="urgent")
    with pytest.raises(training.TrainingProblems):
        training.write(tmp_path / "training", store, stamp=STAMP, render=False)
    assert not (tmp_path / "training" / "data" / "library.json").exists()


def test_library_has_the_team_shape(store, tmp_path):
    lib, _ = _build(store, tmp_path)
    assert set(lib) >= {"schema", "built", "commit", "people", "courses", "facets"}
    assert [c["id"] for c in lib["courses"]] == ["foundations", "markets"]
    assert [l["id"] for l in lib["courses"][0]["lessons"]] == ["creatine-basics", "botanical-basics"]
    l = lib["courses"][0]["lessons"][0]
    assert l["event"] == l["course"] == "foundations" and l["level"] == "Essential" and l["ingredients"] == ["creatine"]
    assert l["minutes"] == 6 and l["version"] == "V2" and l["owner"] == "Invented Training Team"
    assert l["slides"] == 4 and l["thumb"].startswith("data:image/webp")
    assert (tmp_path / "training/build/slides/foundations--creatine-basics.json").exists()
    assert l["quiz"][1] == {"q": "Where is the figure?", "a": "On the second slide (slide 2).", "slide": 2}
    assert len(l["takeaways"]) == 3 and "(my reading)" in l["in_practice"]
    assert lib["facets"]["categories"] == [{"id": "sports", "name": "Sports performance", "lessons": ["foundations--creatine-basics", "markets--sports-market"]}]
    for internal in ("to_check", "added_by", "reviewed_by", "_path"):
        assert internal not in l


def test_related_talks_by_shared_tags(store, tmp_path):
    lib, _ = _build(store, tmp_path, sites={"team": "https://example.invalid/team", "training": ""})
    by = {l["id"]: l for c in lib["courses"] for l in c["lessons"]}
    # creatine + sports + science: the creatine talk; botanicals shares only "science", which alone does not link
    [r] = by["creatine-basics"]["related"]
    assert r["title"] == "Creatine beyond muscle" and r["level"] == "Essential" and r["event"]
    assert r["href"] == "https://example.invalid/team#example-summit-2025--creatine-beyond-muscle"
    assert by["botanical-basics"]["related"] == []
    assert [r["title"] for r in by["sports-market"]["related"]] == ["Creatine beyond muscle"]  # shares the sports category


def test_related_ranks_by_overlap_then_essential():
    talks = [{"id": "a", "event": "e", "_event": "E", "title": "A", "level": "Background", "categories": ["sports"], "ingredients": ["creatine"], "tags": []},
             {"id": "b", "event": "e", "_event": "E", "title": "B", "level": "Essential", "categories": ["sports"], "ingredients": [], "tags": []},
             {"id": "c", "event": "e", "_event": "E", "title": "C", "level": "Background", "categories": ["sports"], "ingredients": [], "tags": []},
             {"id": "d", "event": "e", "_event": "E", "title": "D", "level": "Essential", "categories": [], "ingredients": [], "tags": ["science"]}]
    mod = {"categories": ["sports"], "ingredients": ["creatine"], "tags": ["science"]}
    assert [r["title"] for r in training.related(mod, talks, "")] == ["A", "B", "C"]
    assert len(training.related(mod, talks * 3, "")) == 6


def test_team_talks_and_tags_link_back_to_training(store, tmp_path):
    _, tlib = _build(store, tmp_path, sites={"team": "", "training": "https://example.invalid/training"})
    talk = next(l for c in tlib["courses"] for l in c["lessons"] if l["id"] == "creatine-beyond-muscle")
    assert talk["training"] == [{"title": "Creatine basics", "href": "https://example.invalid/training#foundations--creatine-basics"},
                                {"title": "The sports market", "href": "https://example.invalid/training#markets--sports-market"}]
    sports = next(f for f in tlib["facets"]["categories"] if f["id"] == "sports")
    assert [x["title"] for x in sports["training"]] == ["Creatine basics", "The sports market"]


def test_blank_urls_write_the_route_only(store, tmp_path):
    lib, tlib = _build(store, tmp_path)  # no data/sites.yaml: both addresses blank
    assert lib["courses"][0]["lessons"][0]["related"][0]["href"] == "example-summit-2025--creatine-beyond-muscle"
    talk = next(l for c in tlib["courses"] for l in c["lessons"] if l["id"] == "creatine-beyond-muscle")
    assert talk["training"][0]["href"] == "foundations--creatine-basics"


def test_team_build_without_training_library(store, tmp_path):
    tlib = team.write(tmp_path / "team", store, stamp=STAMP, render=False)
    assert all(l["training"] == [] for c in tlib["courses"] for l in c["lessons"])


def test_team_leak_check_still_covers_training_links(store, tmp_path):
    _build(store, tmp_path)
    p = tmp_path / "training/data/library.json"
    lib = json.loads(p.read_text())
    lib["courses"][0]["lessons"][0]["title"] = "Notes on clear-protein-panel"
    p.write_text(json.dumps(lib))
    d = yaml.safe_load((store / "events/example-summit-2025/sessions/clear-protein-panel/session.yaml").read_text())
    d["confidential"] = True
    (store / "events/example-summit-2025/sessions/clear-protein-panel/session.yaml").write_text(yaml.safe_dump(d, sort_keys=False))
    with pytest.raises(team.TeamLeak):
        team.write(tmp_path / "team", store, stamp=STAMP, render=False)


def test_files_map(store, tmp_path):
    _build(store, tmp_path)
    m = training.files_map(tmp_path / "training")
    assert {"app.js", "styles.css", "data/library.json", "slides/foundations--creatine-basics.json"} <= set(m)


# ---------- narration and video steps (docs/training.md, "Narration and video slides") ----------
import shutil
import subprocess

NARR = MOD + "/narration.md"


def _edit_narration(store, old, new):
    p = store / NARR
    t = p.read_text(); assert old in t
    p.write_text(t.replace(old, new))


def test_parse_narration():
    n = training.parse_narration("# Title\n\n## Slide 1\n\nSource: draft\n\nLine one\ncontinues.\n\nSecond para.\n\n"
                                 "## Video after slide 1\nSource: speaker notes\nWatch it.\n## Notes\nx\n## Slide 2\n\nNo source line.\n")
    assert [s["key"] for s in n["sections"]] == [("slide", 1), ("video", 1), ("slide", 2)]
    assert n["sections"][0] == {"key": ("slide", 1), "heading": "Slide 1", "source": "draft", "script": "Line one continues.\n\nSecond para."}
    assert n["sections"][1]["source"] == "speaker notes" and n["sections"][1]["script"] == "Watch it."
    assert n["sections"][2]["source"] is None and n["unknown"] == ["Notes"]


def test_missing_narration_is_counted_not_a_problem(store):
    assert training.problems(store) == []
    assert training.summary(store).startswith("training: 3 modules, 11 steps (1 videos), narration for 4 (7 not yet written), 2 recorded")
    (store / NARR).unlink()
    shutil.rmtree(store / MOD / "audio")
    assert training.problems(store) == []
    assert "narration for 0 (11 not yet written), 0 recorded" in training.summary(store)


@pytest.mark.parametrize("edit,expect", [
    (lambda s: _edit_narration(s, "## Slide 4", "## Slide 9"), "(Slide 9): the deck has 4 pages"),
    (lambda s: _edit_narration(s, "## Slide 4", "## Slide 1"), "(Slide 1): repeated"),
    (lambda s: _edit_narration(s, "## Video after slide 2", "## Video after slide 3"), "no video follows slide 3"),
    (lambda s: _edit_narration(s, "## Slide 4", "## Outro"), "unknown heading '## Outro'"),
    (lambda s: _edit_narration(s, "Source: speaker notes", "Source: Nathan"), "Source 'Nathan' must be 'speaker notes' or 'draft'"),
    (lambda s: _edit_narration(s, "Source: speaker notes\n", ""), "'Source: speaker notes' or 'Source: draft' line is missing"),
    (lambda s: _edit_narration(s, "closes the deck.", "closes the deck (slide 4)."), "carries no cites"),
    (lambda s: _edit_narration(s, "closes the deck.", "closes the deck. Ask a.person@example.com."), "email address or phone number"),
    (lambda s: _edit_narration(s, "closes the deck.", "closes the whey deck."), "draft script names whey"),
    (lambda s: _edit_narration(s, "The last invented point closes the deck.\n", ""), "(Slide 4): the script is blank"),
    (lambda s: _edit_module(s, videos=[{"after": 2, "url": "https://www.youtube.com/watch?v=abcDEF12345", "id": "abcDEF12345", "channel": "x"}]), "video 1: title is blank"),
    (lambda s: _edit_module(s, videos=[{"after": 7, "url": "https://www.youtube.com/watch?v=abcDEF12345", "id": "abcDEF12345", "title": "t"}]), "after 7 must be a slide number from 1 to 4"),
    (lambda s: _edit_module(s, videos=[{"after": 2, "url": "https://example.com/v", "id": "abcDEF12345", "title": "t"}]), "must be a YouTube link"),
    (lambda s: _edit_module(s, videos=[{"after": 2, "url": "https://youtu.be/zzzZZZ99999", "id": "zzzZZZ99999", "title": "t"}]), "files/youtube-zzzZZZ99999.jpg is missing"),
    (lambda s: _edit_module(s, videos=[{"after": 2, "url": "https://youtu.be/abcDEF12345", "id": "abcDEF12345", "title": "t", "views": 3}]), "unknown key 'views'"),
    (lambda s: _edit_module(s, videos={"after": 2}), "videos must be a list"),
    (lambda s: (s / MOD / "audio/slide-01.mp3").rename(s / MOD / "audio/intro.mp3"), "audio/intro.mp3: name a clip"),
    (lambda s: (s / MOD / "audio/slide-01.mp3").rename(s / MOD / "audio/slide-09.mp3"), "audio/slide-09.mp3: no such step (Slide 9)"),
    (lambda s: (s / MOD / "audio/slide-01.mp3").rename(s / MOD / "audio/video-after-01.mp3"), "no such step (Video after slide 1)"),
    (lambda s: shutil.copy(s / MOD / "audio/slide-02.wav", s / MOD / "audio/slide-02.mp3"), "a second clip for the same step"),
])
def test_narration_problems(store, edit, expect):
    edit(store)
    probs = training.problems(store)
    assert any(expect in p for p in probs), probs


def test_sequence_orders_slides_and_videos(store, tmp_path):
    lib, _ = _build(store, tmp_path)
    l = lib["courses"][0]["lessons"][0]
    seq = l["sequence"]
    assert [(s["kind"], s["slide"]) for s in seq] == [("slide", 1), ("slide", 2), ("video", 2), ("slide", 3), ("slide", 4)]
    assert seq[0]["source"] == "speaker notes" and seq[0]["script"].startswith("Welcome to this invented module")
    assert seq[0]["audio"] == "audio/foundations--creatine-basics/slide-01.m4a" and seq[1]["audio"].endswith("slide-02.m4a")
    assert seq[2]["video"] == {"id": "abcDEF12345", "url": "https://www.youtube.com/watch?v=abcDEF12345", "title": "An invented video",
                               "channel": "Invented Channel", "thumb": "abcDEF12345"}
    assert seq[2]["audio"] == "" and seq[2]["source"] == "draft"
    assert seq[3] == {"kind": "slide", "slide": 3, "script": "", "source": "", "audio": "", "video": None}  # not yet written
    assert all(s["video"] is None for s in seq if s["kind"] == "slide")
    # the thumbnail is in the slide pack, never in library.json
    pack = json.loads((tmp_path / "training/build/slides/foundations--creatine-basics.json").read_text())
    assert pack["videos"]["abcDEF12345"].startswith("data:image/webp;base64,")
    assert "data:image" not in json.dumps(seq)
    other = lib["courses"][0]["lessons"][1]
    assert [s["kind"] for s in other["sequence"]] == ["slide"] * other["slides"] and all(s["audio"] == "" for s in other["sequence"])


@pytest.mark.skipif(not shutil.which("ffprobe"), reason="ffmpeg is not installed")
def test_audio_build_converts_caches_and_publishes(store, tmp_path):
    _build(store, tmp_path)
    d = tmp_path / "training/build/audio/foundations--creatine-basics"
    assert sorted(p.name for p in d.iterdir()) == ["hashes.json", "slide-01.m4a", "slide-02.m4a"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,channels", "-of", "csv=p=0", str(d / "slide-02.m4a")],
                           capture_output=True, text=True, check=True).stdout.strip()
    assert probe == "aac,1"
    first = (d / "slide-01.m4a").stat().st_mtime_ns
    training.write(tmp_path / "training", store, stamp=STAMP)
    assert (d / "slide-01.m4a").stat().st_mtime_ns == first  # cached by the source's hash
    m = training.files_map(tmp_path / "training")
    assert m["audio/foundations--creatine-basics/slide-01.m4a"] == {"from": str(d / "slide-01.m4a"), "contentType": "audio/mp4"}
    # a clip removed from audio/ leaves the build; a module with no clips leaves no folder
    (store / MOD / "audio/slide-02.wav").unlink()
    lib = training.write(tmp_path / "training", store, stamp=STAMP)
    assert sorted(p.name for p in d.iterdir()) == ["hashes.json", "slide-01.m4a"]
    assert lib["courses"][0]["lessons"][0]["sequence"][1]["audio"] == ""
    shutil.rmtree(store / MOD / "audio")
    training.write(tmp_path / "training", store, stamp=STAMP)
    assert not d.exists()
