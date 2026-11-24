"""The team library: a separate, simplified site for Nathan's team (team/, docs/team.md).

`python -m confnotes team` writes:
- team/data/library.json  the courses (events) and lessons (summarised, non-confidential sessions), committed;
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
from pathlib import Path
from typing import Any, Dict, List

from confnotes import DATA, ROOT, build, store

OUT = ROOT / "team"
SLIDE_WIDTH = 1400          # px, rendered deck pages and photos are scaled to this width at most
WEBP_QUALITY = 72
LEVELS = {"high": "Essential", "medium": "Recommended", "low": "Background"}


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


def _lesson(e: Dict[str, Any], s: Dict[str, Any], slides: int) -> Dict[str, Any]:
    sm = s.get("summary") or {}
    return {
        "id": s["id"], "event": e["id"], "title": s["title"], "date": s.get("date"), "start": s.get("start"),
        "format": s.get("format"), "speakers": s.get("speakers") or [], "themes": s.get("themes") or [],
        "ingredients": s.get("ingredients") or [], "level": LEVELS.get(s.get("relevance") or "", "Recommended"),
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


def _photos(folder: Path, photos: Dict[str, str]) -> List[str]:
    from PIL import Image
    return [_webp_data_uri(Image.open(folder / "files" / photos[k])) for k in sorted(photos, key=int)]


def _slides_for(e: Dict[str, Any], s: Dict[str, Any], root: Path, out: Path) -> int:
    """Write the lesson's slide pack (cached by the sources' hash); return the number of slides."""
    folder = Path(root) / "events" / e["id"] / "sessions" / s["id"]
    decks = [folder / "files" / f["name"] for f in _decks(s)]
    sources = decks or ([folder / "files" / s["photos"][k] for k in sorted(s["photos"], key=int)] if s.get("photos") else [])
    if not sources:
        return 0
    h = hashlib.sha256(b"".join(p.read_bytes() for p in sources) + f"{SLIDE_WIDTH}/{WEBP_QUALITY}".encode()).hexdigest()[:16]
    pack = out / "build" / "slides" / f"{e['id']}--{s['id']}.json"
    if pack.exists():
        try:
            cached = json.loads(pack.read_text(encoding="utf-8"))
            if cached.get("hash") == h:
                return len(cached["slides"])
        except (ValueError, KeyError):
            pass
    slides = [u for d in decks for u in _render_pdf(d)] if decks else _photos(folder, s["photos"])
    pack.parent.mkdir(parents=True, exist_ok=True)
    pack.write_text(json.dumps({"hash": h, "slides": slides}), encoding="utf-8")
    return len(slides)


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
    public = {(c["id"], l["id"]) for c in courses for l in c["lessons"]}
    topics = []
    for t in data["themes"]:
        ls = [{"event": x["event"], "session": x["session"]} for x in t.get("sessions", []) if (x["event"], x["session"]) in public]
        if ls:
            topics.append({"id": t["id"], "name": t["name"], "description": t.get("description", ""), "lessons": ls})
    return {"schema": "confnotes.team/1", "built": data["generated"]["date"], "commit": data["generated"]["commit"],
            "courses": courses, "topics": topics}


def write(out: Path = OUT, root: str | Path = DATA, stamp: Dict[str, Any] | None = None, render: bool = True) -> Dict[str, Any]:
    root = Path(root)
    tmp = out / "build" / ".events.tmp.json"
    data = build.build(tmp, root, stamp)
    tmp.unlink(missing_ok=True)
    lib = library(data, root, out, render)
    text = json.dumps(lib, indent=1, ensure_ascii=False)
    leaks = [t for t in _forbidden_terms(store.load(root), data, root) if re.search(re.escape(t), text, re.I)]
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
