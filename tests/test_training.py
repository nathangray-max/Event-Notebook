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
