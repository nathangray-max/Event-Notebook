"""The team library: a separate, simplified site for Nathan's team (team/, docs/team.md).

`python -m confnotes team` writes:
- team/data/library.json  the courses (events) and lessons (summarised, non-confidential sessions), committed;
- each talk and each tag value carries `training: [{title, href}]`, the training modules on the same tags, read from
  training/data/library.json when the training library has been built (docs/training.md);
- team/build/slides/<event>--<session>.json  each lesson's slides as an array of image data URIs (deck pages rendered
  from the original PDF, otherwise the slide photos), generated, git-ignored, published beside the page.

Confidential sessions never enter the team build, nor do leads, transcripts, Nathan's notes, open questions or follow-ups.
The build refuses when public text names a confidential session or a confidential lead's company.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

from confnotes import DATA, ROOT, build, store

OUT = ROOT / "team"
SLIDE_WIDTH = 1400          # px, rendered deck pages and photos are scaled to this width at most
WEBP_QUALITY = 72
LEVELS = {"high": "Essential", "medium": "Recommended", "low": "Background"}


# The same speaker under two billed names (Nathan's notes treat them as one person); the first is shown.
PEOPLE_ALIASES = {"Nicholas Morgan": "Nick Morgan"}
TITLES = re.compile(r"^(dr|prof|professor)\.?\s+", re.I)


def _slug(s: str) -> str:
    plain = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()  # Pavlová -> Pavlova
    return re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-")


def person_id(sp: Dict[str, Any]) -> str:
    """A stable id for a speaker's page, or '' for someone who gets none (consumer panellists, unnamed speakers).
    A first name alone is told apart by the organisation (two different Miguels)."""
    name, org = str(sp.get("name") or ""), str(sp.get("organisation") or "")
    if not name or "panellist" in org.lower() or name.lower().startswith("not named"):
        return ""
    base = PEOPLE_ALIASES.get(name, name)
    base = TITLES.sub("", re.sub(r"\s*\(.*?\)", "", base)).strip()
    sid = _slug(base)
    if " " not in base and org:
        sid += "-" + _slug(" ".join(re.sub(r"\(.*?\)", "", org).split()[:2]))
    return sid


# ---------- links between the team library and the training library (docs/training.md) ----------
# Both builds score shared tags the same way: an ingredient group counts most, then a market category, then an insight
# type. Insight types alone are too broad to link on (most talks are "science"), so a link needs a shared ingredient
# group or category whenever the item has either.
WEIGHTS = {"ingredients": 3, "categories": 2, "tags": 1}
LEVEL_RANK = {"Essential": 0, "Recommended": 1, "Background": 2}


def overlap(a: Dict[str, Any], b: Dict[str, Any]) -> int:
    """How strongly two items (talks or modules: categories, ingredients, tags as id lists) share tags; 0 = no link."""
    shared = {k: len(set(a.get(k) or []) & set(b.get(k) or [])) for k in WEIGHTS}
    if (a.get("ingredients") or a.get("categories")) and not (shared["ingredients"] or shared["categories"]):
        return 0
    return sum(WEIGHTS[k] * n for k, n in shared.items())


def site_href(url: str, route: str) -> str:
    """A link into another library: its artifact url + '#' + route, or the route alone while the url is blank (the
    front end then shows the link as plain text naming the other library)."""
    return f"{url}#{route}" if url else route


def load_training(path: Path) -> List[Dict[str, Any]]:
    """The training library's modules (training/data/library.json, the training build's output); [] when it does not exist."""
    if not Path(path).exists():
        return []
    lib = json.loads(Path(path).read_text(encoding="utf-8"))
    return [dict(l, course=c["id"]) for c in lib.get("courses") or [] for l in c.get("lessons") or []]


def add_training_links(lib: Dict[str, Any], modules: List[Dict[str, Any]], url: str, most: int = 4) -> None:
    """`training: [{title, href}]` on each talk (modules sharing tags, best overlap first, Essential first) and on each
    facet value (modules carrying it, Essential first, in course order)."""
    def link(m):
        return {"title": m["title"], "href": site_href(url, f"{m['course']}--{m['id']}")}
    order = {(m["course"], m["id"]): i for i, m in enumerate(modules)}
    for c in lib["courses"]:
        for l in c["lessons"]:
            scored = [(overlap(l, m), m) for m in modules]
            scored = sorted([x for x in scored if x[0]], key=lambda x: (-x[0], LEVEL_RANK.get(x[1].get("level"), 1), order[(x[1]["course"], x[1]["id"])]))
            l["training"] = [link(m) for _, m in scored[:most]]
    for kind, fs in lib["facets"].items():
        for f in fs:
            ms = sorted([m for m in modules if f["id"] in (m.get(kind) or [])], key=lambda m: (LEVEL_RANK.get(m.get("level"), 1), order[(m["course"], m["id"])]))
            f["training"] = [link(m) for m in ms[:most]]


class TeamLeak(Exception):
    pass


def _forbidden_terms(st: Dict[str, Any], data: Dict[str, Any], root: Path) -> List[str]:
    """Words that must never appear in the team build: confidential session ids and confidential leads' companies."""
    terms = [s["id"] for e in data["events"] for s in e["sessions"] if s.get("confidential")]
    for lead in store.load_leads(root):
        if lead.get("confidential"):
            name = str(lead.get("company", "")).split(" (")[0].strip()
            if name:
                terms.append(name)
    return terms


def _leaks(terms: List[str], text: str) -> List[str]:
    """The forbidden terms that appear in the build's words. Embedded images (data: URIs) are skipped, since their base64
    can spell any short name by chance; a term counts only as a whole word."""
    words = re.sub(r"data:[a-z]+/[a-z0-9.+-]+;base64,[A-Za-z0-9+/=]+", "", text)
    return [t for t in terms if re.search(r"(?<![A-Za-z0-9])" + re.escape(t) + r"(?![A-Za-z0-9])", words, re.I)]


def _lesson(e: Dict[str, Any], s: Dict[str, Any], slides: int) -> Dict[str, Any]:
    sm = s.get("summary") or {}
    return {
        "id": s["id"], "event": e["id"], "title": s["title"], "date": s.get("date"), "start": s.get("start"),
        "format": s.get("format"), "speakers": [dict(sp, person=person_id(sp)) for sp in s.get("speakers") or [] if isinstance(sp, dict)],
        "categories": s.get("categories") or [], "tags": s.get("tags") or [], "ingredients": s.get("ingredient_groups") or [], "level": LEVELS.get(s.get("relevance") or "", "Recommended"),
        "summary": sm.get("Summary", ""), "takeaways": [t["text"] for t in s.get("takeaways") or []],
        "for_us": sm.get("For Vita Actives", ""), "quotes": [q["text"] for q in s.get("quotes") or []],
        "detail": sm.get("Detail", ""), "key_slides": s.get("key_slides") or [],
        "slides": slides, "slide_source": "deck" if _decks(s) else ("photos" if s.get("photos") else None),
        "deck_names": [f["name"] for f in _decks(s)],
    }


def _decks(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [f for f in s.get("files") or [] if str(f["name"]).lower().endswith(".pdf")]


def _webp_data_uri(img) -> str:
    from PIL import Image
    if img.width > SLIDE_WIDTH:
        img = img.resize((SLIDE_WIDTH, round(img.height * SLIDE_WIDTH / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "WEBP", quality=WEBP_QUALITY, method=4)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def _render_pdf(pdf: Path) -> List[str]:
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "110", "-png", str(pdf), str(Path(tmp) / "p")], check=True, capture_output=True)
        pages = sorted(Path(tmp).glob("p-*.png"), key=lambda p: int(p.stem.split("-")[-1]))
        return [_webp_data_uri(Image.open(p)) for p in pages]


def slide_pack(pack: Path, sources: List[Path], decks: bool) -> int:
    """Write a slide pack (cached by the sources' hash): the PDF decks' pages rendered, or the photos in order.
    Returns the number of slides. Shared with the training build (confnotes/training.py)."""
    from PIL import Image
    if not sources:
        return 0
    h = hashlib.sha256(b"".join(p.read_bytes() for p in sources) + f"{SLIDE_WIDTH}/{WEBP_QUALITY}".encode()).hexdigest()[:16]
    if pack.exists():
        try:
            cached = json.loads(pack.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                return len(cached["slides"])
        except (ValueError, KeyError):
            pass
    slides = [u for d in sources for u in _render_pdf(d)] if decks else [_webp_data_uri(Image.open(p)) for p in sources]
    pack.parent.mkdir(parents=True, exist_ok=True)
    pack.write_text(json.dumps({"hash": h, "slides": slides}), encoding="utf-8")
    return len(slides)


def _slides_for(e: Dict[str, Any], s: Dict[str, Any], root: Path, out: Path) -> int:
    """Write the lesson's slide pack (cached by the sources' hash); return the number of slides."""
    folder = Path(root) / "events" / e["id"] / "sessions" / s["id"]
    decks = [folder / "files" / f["name"] for f in _decks(s)]
    sources = decks or ([folder / "files" / s["photos"][k] for k in sorted(s["photos"], key=int)] if s.get("photos") else [])
    return slide_pack(out / "build" / "slides" / f"{e['id']}--{s['id']}.json", sources, bool(decks))


def _thumb(out: Path, e: Dict[str, Any], s: Dict[str, Any], width: int) -> str:
    """The lesson's first slide, small, as a data URI (for catalogue cards); '' when the lesson has no slides."""
    from PIL import Image
    pack = out / "build" / "slides" / f"{e['id']}--{s['id']}.json"
    if not pack.exists():
        return ""
    first = json.loads(pack.read_text(encoding="utf-8"))["slides"][0]
    img = Image.open(io.BytesIO(base64.b64decode(first.split(",", 1)[1])))
    img = img.resize((width, round(img.height * width / img.width)), Image.LANCZOS)
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "WEBP", quality=60)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def library(data: Dict[str, Any], root: Path, out: Path, render: bool = True) -> Dict[str, Any]:
    courses = []
    for e in data["events"]:
        lessons = []
        for s in e["sessions"]:
            if s.get("confidential") or not s.get("has_summary"):
                continue
            n = _slides_for(e, s, root, out) if render else 0
            lesson = _lesson(e, s, n)
            lesson["thumb"] = _thumb(out, e, s, 360) if n else ""
            lessons.append(lesson)
        if not lessons:
            continue
        lessons.sort(key=lambda l: ((l["date"] or ""), (l["start"] or "")))
        courses.append({"id": e["id"], "name": e["name"], "short": e.get("short") or e["name"], "start": e.get("start"),
                        "end": e.get("end"), "city": e.get("city"), "country": e.get("country"),
                        "organiser": e.get("organiser"), "description": e.get("description"), "lessons": lessons})
    # the three kinds of tag (data/facets.yaml): each value with the talks that carry it; values no talk carries are left out
    facets = {}
    for kind, field in (("categories", "categories"), ("ingredients", "ingredients"), ("tags", "tags")):
        facets[kind] = []
        for f in data.get("facets", {}).get(kind) or []:
            ls = [f"{c['id']}--{l['id']}" for c in courses for l in c["lessons"] if f["id"] in l[field]]
            if ls:
                facets[kind].append({"id": f["id"], "name": f["name"], "lessons": ls})
    people: Dict[str, Dict[str, Any]] = {}
    for c in courses:
        for l in c["lessons"]:
            for sp in l["speakers"]:
                if not sp["person"]:
                    continue
                p = people.setdefault(sp["person"], {"id": sp["person"], "name": PEOPLE_ALIASES.get(sp["name"], sp["name"]),
                                                     "organisations": [], "lessons": []})
                org = re.sub(r"\s*\(.*?\)", "", str(sp.get("organisation") or "")).strip()
                if org and org not in p["organisations"]:
                    p["organisations"].append(org)
                k = f"{c['id']}--{l['id']}"
                if k not in p["lessons"]:
                    p["lessons"].append(k)
    return {"schema": "confnotes.team/1", "built": data["generated"]["date"], "commit": data["generated"]["commit"],
            "people": sorted(people.values(), key=lambda p: TITLES.sub("", p["name"]).split()[-1].lower()),
            "courses": courses, "facets": facets}


def write(out: Path = OUT, root: str | Path = DATA, stamp: Dict[str, Any] | None = None, render: bool = True) -> Dict[str, Any]:
    root = Path(root)
    tmp = out / "build" / ".events.tmp.json"
    data = build.build(tmp, root, stamp)
    tmp.unlink(missing_ok=True)
    lib = library(data, root, out, render)
    # the training library beside this one (training/data/library.json): read only if built
    add_training_links(lib, load_training(out.parent / "training" / "data" / "library.json"), store.load_sites(root)["training"])
    text = json.dumps(lib, indent=1, ensure_ascii=False)
    leaks = _leaks(_forbidden_terms(store.load(root), data, root), text)
    if leaks:
        raise TeamLeak("the team build names confidential items, nothing written: " + ", ".join(sorted(set(leaks))))
    # slide packs of lessons that are no longer public are removed
    keep = {f"{c['id']}--{l['id']}.json" for c in lib["courses"] for l in c["lessons"]}
    packs = out / "build" / "slides"
    if packs.is_dir():
        for p in packs.glob("*.json"):
            if p.name not in keep:
                p.unlink()
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "library.json").write_text(text + "\n", encoding="utf-8")
    return lib


def files_map(out: Path = OUT) -> Dict[str, str]:
    """Published path -> local file, for publishing the team site (team/ARTIFACT.md)."""
    m = {"app.js": str(out / "app.js"), "styles.css": str(out / "styles.css"), "data/library.json": str(out / "data" / "library.json")}
    lib = json.loads((out / "data" / "library.json").read_text(encoding="utf-8"))
    for c in lib["courses"]:
        for l in c["lessons"]:
            if l["slides"]:
                name = f"{c['id']}--{l['id']}.json"
                m[f"slides/{name}"] = str(out / "build" / "slides" / name)
    return m
