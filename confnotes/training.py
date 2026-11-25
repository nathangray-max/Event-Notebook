"""The training library (pilot): onboarding and training modules on topics and ingredients (docs/training.md).

    load(root)       -> the courses (data/training/<course>/course.yaml), each with its modules (module.yaml + summary.md)
    problems(root)   -> what breaks the spec; [] when clean (`python -m confnotes check` runs it too)
    write(...)       -> training/data/library.json and the slide packs in training/build/slides/<course>--<module>.json,
                        plus the narration clips converted to small mono AAC in training/build/audio/<course>--<module>/
    summary(root)    -> one line: modules, steps, narration sections written and missing, clips

Narration (docs/training.md, "Narration and video slides"): each module may carry narration.md (`## Slide N` and
`## Video after slide N` sections, a `Source:` line, then the script), `videos` in module.yaml (YouTube links shown as
their own step after slide N, thumbnail in files/youtube-<id>.jpg) and audio/ (one clip per step, slide-NN.<ext> or
video-after-NN.<ext>). Each lesson gets `sequence`: its steps in order, each {kind, slide, script, source, audio, video};
a video step's thumbnail goes into the slide pack (`videos`: {id: data URI}), never into library.json.

The library has the team library's shape (courses -> lessons, people, facets) so the same front end runs it; each module
also carries its quiz, minutes, version, owner and `related`: the team library's talks on the same tags, read from
team/data/library.json (the team build's output), never from session files.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List

import yaml

from confnotes import DATA, ROOT, build, store, team

OUT = ROOT / "training"
LEVELS = team.LEVELS                     # high/medium/low -> Essential/Recommended/Background
STATUS = {"draft", "reviewed"}
MODULE_KEYS = ["id", "title", "course", "order", "owner", "version", "level", "audience", "minutes", "categories", "tags",
               "ingredients", "deck", "source", "status", "reviewed_by", "to_check", "added", "added_by"]
REQUIRED = ["id", "title", "course", "order", "level", "minutes", "tags", "deck", "source", "status", "added", "added_by"]
TEXT_KEYS = ["title", "owner", "version", "audience", "deck", "source", "reviewed_by", "to_check", "added_by"]
LIST_KEYS = ["categories", "tags", "ingredients"]
SECTIONS = ["Summary", "Key learnings", "In practice", "Check your understanding"]
OPTIONAL = ["Key slides", "Detail"]
SUMMARY_MAX_WORDS = 220
LEARNINGS_MAX = 6
QUIZ_MIN, QUIZ_MAX = 3, 5
KEY_SLIDES_MAX = 4
RELATED_MAX = 6
SLIDE = re.compile(r"\(slides? (\d+)[^)]*\)")  # (slide 7), (slides 3-5), (slide 7, speaker notes)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<![\w-])(?:\+\d{1,3}[ -]?(?:\(0\)[ -]?)?|0)\d{2,5}[ -]?\d{3,4}[ -]?\d{3,4}(?![\w-])")  # +44 20 7946 0000, 020 7946 0000
WHEY = re.compile(r"\bwhey\b", re.I)
# narration and video steps
OPTIONAL_KEYS = ["videos"]
INTERNAL = {"_path", "summary_md", "headings", "sections", "pages", "narration", "clips"}
NARR_SOURCES = {"speaker notes", "draft"}
NARR_HEAD = re.compile(r"^## (?:Slide (\d+)|Video after slide (\d+))\s*$")
VIDEO_KEYS = ["after", "url", "id", "title", "channel"]
VIDEO_REQUIRED = ["after", "url", "id", "title"]
YT_ID = re.compile(r"^[A-Za-z0-9_-]{6,20}$")
YT_URL = re.compile(r"^https://(?:www\.|m\.)?(?:youtube\.com/|youtu\.be/)")
AUDIO_EXT = {".m4a", ".mp3", ".wav", ".aac", ".ogg", ".oga", ".opus", ".webm", ".flac", ".aif", ".aiff", ".caf", ".mp4", ".wma", ".amr"}
CLIP = re.compile(r"^(slide|video-after)-(\d+)$")
AUDIO_SETTINGS = "aac/mono/48k/v1"         # part of the cache key: change it to re-encode every clip
VIDEO_THUMB_WIDTH = 640


# ---------- loading ----------
def module_file(folder: Path, name: str) -> Path:
    """A file named in module.yaml (deck, source): a name in files/, or a path from the module folder ('files/x.pdf')."""
    name = str(name or "")
    return folder / name if name.startswith("files/") else folder / "files" / name



def _yaml(path: Path) -> Dict[str, Any]:
    d = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(d, dict):
        raise ValueError(f"{path}: expected a mapping")
    return d


def deck_pages(path: Path) -> int:
    """The number of pages of a PDF deck (0 when it cannot be read)."""
    try:
        out = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True).stdout
        m = re.search(r"^Pages:\s+(\d+)", out, re.M)
        return int(m.group(1)) if m else 0
    except (OSError, subprocess.CalledProcessError):
        return 0


def quiz(text: str) -> List[Dict[str, Any]]:
    """`- Q: ...` lines, each followed by `  A: ... (slide N)`: [{q, a, slide}] (a is '' when the answer line is missing)."""
    out: List[Dict[str, Any]] = []
    for line in text.splitlines():
        q = re.match(r"^\s*[-*]\s*Q:\s*(.+)$", line)
        a = re.match(r"^\s+A:\s*(.+)$", line) or (re.match(r"^\s*A:\s*(.+)$", line) if out else None)
        if q:
            out.append({"q": q.group(1).strip(), "a": "", "slide": 0})
        elif a and out and not out[-1]["a"]:
            m = SLIDE.search(a.group(1))
            out[-1]["a"], out[-1]["slide"] = a.group(1).strip(), int(m.group(1)) if m else 0
        elif out and line.strip() and not line.startswith("#"):
            k = "a" if out[-1]["a"] else "q"
            out[-1][k] += " " + line.strip()
            if k == "a" and not out[-1]["slide"]:
                m = SLIDE.search(out[-1]["a"])
                out[-1]["slide"] = int(m.group(1)) if m else 0
    return out


def _blocks(text: str) -> List[str]:
    """A section's bullets, or its paragraphs when it has none."""
    b = store.bullets(text)
    return b if b else [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]


def load_module(folder: Path) -> Dict[str, Any]:
    m = _yaml(folder / "module.yaml")
    m["_path"] = str(folder)
    md = (folder / "summary.md").read_text(encoding="utf-8") if (folder / "summary.md").exists() else ""
    m["summary_md"] = md
    m["headings"] = [l[3:].strip() for l in md.splitlines() if l.startswith("## ")]
    m["sections"] = store.split_sections(md) if md else {}
    deck = module_file(folder, m.get("deck"))
    m["pages"] = deck_pages(deck) if m.get("deck") and deck.is_file() else 0
    nf = folder / "narration.md"
    m["narration"] = parse_narration(nf.read_text(encoding="utf-8")) if nf.exists() else None
    m["clips"] = clips(folder)
    return m


def parse_narration(text: str) -> Dict[str, Any]:
    """narration.md -> {"sections": [{key: ("slide"|"video", N), heading, source, script}], "unknown": [headings]}.
    `source` is None when the section has no `Source:` line; the script is the rest, paragraphs kept, lines joined."""
    sections: List[Dict[str, Any]] = []
    unknown: List[str] = []
    cur: Dict[str, Any] | None = None
    body: List[str] = []

    def close() -> None:
        if cur is None:
            return
        lines = list(body)
        while lines and not lines[0].strip():
            lines.pop(0)
        if lines and re.match(r"^\s*Source:", lines[0], re.I):
            cur["source"] = lines.pop(0).split(":", 1)[1].strip()
        paras = [" ".join(l.strip() for l in p.splitlines() if l.strip()) for p in re.split(r"\n\s*\n", "\n".join(lines))]
        cur["script"] = "\n\n".join(p for p in paras if p)
        sections.append(cur)

    for line in text.splitlines():
        if line.startswith("## "):
            close()
            h = NARR_HEAD.match(line.rstrip())
            if h:
                cur = {"key": ("slide", int(h.group(1))) if h.group(1) else ("video", int(h.group(2))),
                       "heading": line[3:].strip(), "source": None, "script": ""}
            else:
                cur = None
                unknown.append(line[3:].strip())
            body = []
        elif cur is not None:
            body.append(line)
    close()
    return {"sections": sections, "unknown": unknown}


def clips(folder: Path) -> Dict[str, Any]:
    """The recordings in the module's audio/ folder: {"by_key": {("slide"|"video", N): path}, "bad": [names], "dupes": [names]}."""
    out: Dict[str, Any] = {"by_key": {}, "bad": [], "dupes": []}
    a = folder / "audio"
    if not a.is_dir():
        return out
    for p in sorted(a.iterdir()):
        if p.name.startswith(".") or not p.is_file():
            continue
        m = CLIP.match(p.stem)
        if not m or p.suffix.lower() not in AUDIO_EXT:
            out["bad"].append(p.name)
            continue
        k = ("slide" if m.group(1) == "slide" else "video", int(m.group(2)))
        if k in out["by_key"]:
            out["dupes"].append(p.name)
        else:
            out["by_key"][k] = p
    return out


def videos(m: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The module's well-formed video entries (the checks report the rest)."""
    v = m.get("videos") or []
    return [x for x in v if isinstance(x, dict) and isinstance(x.get("after"), int)] if isinstance(v, list) else []


def expected_steps(m: Dict[str, Any]) -> List[tuple]:
    """The step keys in order: ("slide", N) for each page, ("video", N) right after slide N when a video follows it."""
    after = {v["after"] for v in videos(m)}
    keys: List[tuple] = []
    for n in range(1, (m.get("pages") or 0) + 1):
        keys.append(("slide", n))
        if n in after:
            keys.append(("video", n))
    return keys


def _key_name(k: tuple) -> str:
    return f"Slide {k[1]}" if k[0] == "slide" else f"Video after slide {k[1]}"


def _clip_name(k: tuple) -> str:
    return f"{'slide' if k[0] == 'slide' else 'video-after'}-{k[1]:02d}.m4a"


def load(root: str | Path = DATA) -> List[Dict[str, Any]]:
    """The courses in order, each with `modules` in order."""
    base = Path(root) / "training"
    courses = []
    if not base.is_dir():
        return courses
    for cf in sorted(base.iterdir()):
        if not (cf / "course.yaml").exists():
            continue
        c = _yaml(cf / "course.yaml")
        c["_path"], c["_folder"] = str(cf), cf.name
        mods = cf / "modules"
        c["modules"] = [load_module(p) for p in sorted(mods.iterdir()) if (p / "module.yaml").exists()] if mods.is_dir() else []
        c["modules"].sort(key=lambda m: (m.get("order") if isinstance(m.get("order"), int) else 999, str(m.get("id"))))
        courses.append(c)
    courses.sort(key=lambda c: (c.get("order") if isinstance(c.get("order"), int) else 999, c["_folder"]))
    return courses


# ---------- the checks ----------
def _cites_ok(out: List[str], where: str, text: str, pages: int) -> None:
    for n in SLIDE.findall(text):
        if pages and not 1 <= int(n) <= pages:
            out.append(f"{where}: cites slide {n} but the deck has {pages} pages")


def _our_text(out: List[str], where: str, text: str, name: str) -> None:
    if WHEY.search(text):
        out.append(f"{where}: {name} names whey; our own text never does (keep the deck's wording in Detail)")
    if EMAIL.search(text) or PHONE.search(text):
        out.append(f"{where}: {name} carries an email address or phone number")


def module_problems(m: Dict[str, Any], course: str, facets: Dict[str, Any]) -> List[str]:
    folder = Path(m["_path"])
    where = f"training/{course}/{folder.name}"
    out: List[str] = []
    for k in MODULE_KEYS:
        if k not in m:
            out.append(f"{where}/module.yaml: key '{k}' is missing")
    for k in set(m) - set(MODULE_KEYS) - set(OPTIONAL_KEYS) - INTERNAL:
        out.append(f"{where}/module.yaml: unknown key '{k}'")
    for k in REQUIRED:
        if k in m and m[k] in (None, "", []):
            out.append(f"{where}/module.yaml: {k} is blank")
    if m.get("id") != folder.name or not store.ID_RE.match(str(m.get("id") or "")):
        out.append(f"{where}/module.yaml: id '{m.get('id')}' must be the folder name (lowercase, hyphens)")
    if m.get("course") != course:
        out.append(f"{where}/module.yaml: course '{m.get('course')}' must be '{course}'")
    for k in ("order", "minutes"):
        if k in m and m[k] not in (None, "") and (not isinstance(m[k], int) or isinstance(m[k], bool) or m[k] < 1):
            out.append(f"{where}/module.yaml: {k} must be a whole number from 1")
    for k in TEXT_KEYS:
        if m.get(k) is not None and not isinstance(m[k], str):
            out.append(f"{where}/module.yaml: {k} must be text (quote it)")
    for k in LIST_KEYS:
        if k in m and not isinstance(m[k] or [], list):
            out.append(f"{where}/module.yaml: {k} must be a list")
    if m.get("level") not in (None, "") and m["level"] not in LEVELS:
        out.append(f"{where}/module.yaml: level '{m['level']}' not in {sorted(LEVELS)}")
    if m.get("status") not in (None, "") and m["status"] not in STATUS:
        out.append(f"{where}/module.yaml: status '{m['status']}' not in {sorted(STATUS)}")
    if m.get("status") == "reviewed" and not m.get("reviewed_by"):
        out.append(f"{where}/module.yaml: status is reviewed but reviewed_by is blank")
    if m.get("added") not in (None, "") and not store.DATE_RE.match(str(m["added"])):
        out.append(f"{where}/module.yaml: added '{m['added']}' is not YYYY-MM-DD")
    ids = {k: {f.get("id") for f in facets.get(k) or []} for k in ("categories", "tags")}
    for k in ("categories", "tags"):
        for x in m.get(k) or [] if isinstance(m.get(k) or [], list) else []:
            if x not in ids[k]:
                out.append(f"{where}/module.yaml: {k[:-1] if k == 'tags' else 'category'} '{x}' is not in data/facets.yaml")
    for k in ("deck", "source"):
        if m.get(k) and not module_file(folder, m[k]).is_file():
            out.append(f"{where}/module.yaml: {k} '{m[k]}' is not in files/")
    if m.get("deck") and not str(m["deck"]).lower().endswith(".pdf"):
        out.append(f"{where}/module.yaml: deck '{m['deck']}' must be a pdf (render the pptx to pdf)")
    elif m.get("deck") and module_file(folder, m["deck"]).is_file() and not m["pages"]:
        out.append(f"{where}/module.yaml: deck '{m['deck']}' has no readable pages")
    for k in TEXT_KEYS:
        if k not in ("deck", "source") and isinstance(m.get(k), str) and (EMAIL.search(m[k]) or PHONE.search(m[k])):
            out.append(f"{where}/module.yaml: {k} carries an email address or phone number")

    out.extend(narration_problems(m, where))

    # summary.md
    sw = f"{where}/summary.md"
    if not m["summary_md"]:
        return out + [f"{sw}: missing"]
    known = SECTIONS + OPTIONAL
    for h in m["headings"]:
        if h not in known:
            out.append(f"{sw}: unknown heading '{h}' (allowed, in order: {', '.join(known)})")
    present = [h for h in m["headings"] if h in known]
    for h in SECTIONS:
        if h not in present:
            out.append(f"{sw}: section '## {h}' is missing")
    if present != [h for h in known if h in present] or len(present) != len(set(present)):
        out.append(f"{sw}: sections out of order or repeated (order: {', '.join(known)})")
    sec, pages = m["sections"], m["pages"]
    summ = sec.get("Summary", "")
    words = len(summ.split())
    if words >= SUMMARY_MAX_WORDS:
        out.append(f"{sw}: Summary is {words} words; keep it under {SUMMARY_MAX_WORDS}")
    if store.CITE_IN_PROSE.search(summ):
        out.append(f"{sw}: Summary carries cites; it is prose")
    learnings = store.bullets(sec.get("Key learnings", ""))
    if len(learnings) > LEARNINGS_MAX:
        out.append(f"{sw}: {len(learnings)} key learnings; keep at most {LEARNINGS_MAX}")
    if "Key learnings" in sec and not learnings:
        out.append(f"{sw}: Key learnings has no bullets")
    for i, b in enumerate(learnings, 1):
        if not SLIDE.search(b):
            out.append(f"{sw}: key learning {i} has no (slide N) cite")
    for i, b in enumerate(_blocks(sec.get("In practice", "")), 1):
        if not SLIDE.search(b) and "my reading" not in b.lower():
            out.append(f"{sw}: In practice item {i} has no (slide N) cite and is not marked 'my reading'")
    qs = quiz(sec.get("Check your understanding", ""))
    if "Check your understanding" in sec and not QUIZ_MIN <= len(qs) <= QUIZ_MAX:
        out.append(f"{sw}: Check your understanding has {len(qs)} questions; give {QUIZ_MIN} to {QUIZ_MAX} ('- Q: ...' then '  A: ... (slide N)')")
    for i, q in enumerate(qs, 1):
        if not q["a"]:
            out.append(f"{sw}: question {i} has no '  A: ...' line")
        elif not q["slide"]:
            out.append(f"{sw}: answer {i} has no (slide N) cite")
    if "Key slides" in sec:
        ks = store.bullets(sec["Key slides"]) or [l.strip() for l in sec["Key slides"].splitlines() if l.strip()]
        if len(ks) > KEY_SLIDES_MAX:
            out.append(f"{sw}: {len(ks)} key slides; keep at most {KEY_SLIDES_MAX}")
        for b in ks:
            if not re.match(r"^\(slide \d+\)", b):
                out.append(f"{sw}: key slide '{b[:40]}' must start '(slide N)' then a few words")
    for name in SECTIONS + OPTIONAL:
        _cites_ok(out, sw + f" ({name})", sec.get(name, ""), pages)
    for name in ("Summary", "Key learnings", "In practice", "Check your understanding"):
        _our_text(out, sw, sec.get(name, ""), name)
    if EMAIL.search(sec.get("Detail", "")):
        out.append(f"{sw}: Detail carries an email address")
    return out


def narration_problems(m: Dict[str, Any], where: str) -> List[str]:
    """videos in module.yaml, narration.md and the audio/ clips. Sections not yet written are not problems (summary())."""
    folder, pages, out = Path(m["_path"]), m.get("pages") or 0, []
    yw = f"{where}/module.yaml"
    vs = m.get("videos")
    if vs is not None and not isinstance(vs, list):
        out.append(f"{yw}: videos must be a list of {{after, url, id, title, channel}}")
        vs = []
    seen_after: Dict[int, str] = {}
    for i, v in enumerate(vs or [], 1):
        vw = f"{yw}: video {i}"
        if not isinstance(v, dict):
            out.append(f"{vw} must be a mapping of {', '.join(VIDEO_KEYS)}"); continue
        for k in VIDEO_REQUIRED:
            if v.get(k) in (None, ""):
                out.append(f"{vw}: {k} is blank")
        for k in set(v) - set(VIDEO_KEYS):
            out.append(f"{vw}: unknown key '{k}'")
        a = v.get("after")
        if a is not None and (not isinstance(a, int) or isinstance(a, bool) or (pages and not 1 <= a <= pages)):
            out.append(f"{vw}: after {a!r} must be a slide number from 1 to {pages}")
        elif isinstance(a, int):
            if a in seen_after:
                out.append(f"{vw}: a video already follows slide {a} (one per slide)")
            seen_after[a] = str(v.get("id"))
        for k in ("url", "id", "title", "channel"):
            if v.get(k) is not None and not isinstance(v[k], str):
                out.append(f"{vw}: {k} must be text (quote it)")
        vid, url = str(v.get("id") or ""), str(v.get("url") or "")
        if vid and not YT_ID.match(vid):
            out.append(f"{vw}: id '{vid}' is not a YouTube video id")
        if url and (not YT_URL.match(url) or (vid and vid not in url)):
            out.append(f"{vw}: url '{url}' must be a YouTube link to video '{vid}'")
        if vid and YT_ID.match(vid) and not (folder / "files" / f"youtube-{vid}.jpg").is_file():
            out.append(f"{vw}: the thumbnail files/youtube-{vid}.jpg is missing")

    nw = f"{where}/narration.md"
    n = m.get("narration")
    if n is not None:
        for h in n["unknown"]:
            out.append(f"{nw}: unknown heading '## {h}' (use '## Slide N' or '## Video after slide N')")
        keys = set()
        for s in n["sections"]:
            k, sw = s["key"], f"{nw} ({s['heading']})"
            if k in keys:
                out.append(f"{sw}: repeated")
            keys.add(k)
            if k[0] == "slide" and pages and not 1 <= k[1] <= pages:
                out.append(f"{sw}: the deck has {pages} pages")
            if k[0] == "video" and k[1] not in seen_after:
                out.append(f"{sw}: no video follows slide {k[1]} in module.yaml videos")
            if s["source"] is None:
                out.append(f"{sw}: the 'Source: speaker notes' or 'Source: draft' line is missing")
            elif s["source"].lower() not in NARR_SOURCES:
                out.append(f"{sw}: Source '{s['source']}' must be 'speaker notes' or 'draft'")
            if not s["script"]:
                out.append(f"{sw}: the script is blank")
            if SLIDE.search(s["script"]):
                out.append(f"{sw}: a script is spoken; it carries no cites")
            if EMAIL.search(s["script"]) or PHONE.search(s["script"]):
                out.append(f"{sw}: the script carries an email address or phone number")
            if (s["source"] or "").lower() == "draft" and WHEY.search(s["script"]):
                out.append(f"{sw}: a draft script names whey; our own text never does")

    aw = f"{where}/audio"
    c = m.get("clips") or {"by_key": {}, "bad": [], "dupes": []}
    for name in c["bad"]:
        out.append(f"{aw}/{name}: name a clip slide-NN.<ext> or video-after-NN.<ext> (an audio format such as m4a, mp3, wav)")
    for name in c["dupes"]:
        out.append(f"{aw}/{name}: a second clip for the same step")
    expected = set(expected_steps(m))
    for k, p in sorted(c["by_key"].items()):
        if pages and k not in expected:
            out.append(f"{aw}/{p.name}: no such step ({_key_name(k)})")
    return out


def summary(root: str | Path = DATA) -> str:
    """One line for `check`: modules, steps, narration written and missing (missing is not a problem), clips."""
    try:
        courses = load(root)
    except (ValueError, yaml.YAMLError):
        return "training: cannot be read"
    mods = [m for c in courses for m in c["modules"]]
    steps = written = recorded = 0
    for m in mods:
        keys = expected_steps(m)
        have = {s["key"] for s in (m.get("narration") or {}).get("sections", [])}
        steps += len(keys)
        written += sum(1 for k in keys if k in have)
        recorded += sum(1 for k in keys if k in (m.get("clips") or {}).get("by_key", {}))
    vids = sum(len(videos(m)) for m in mods)
    return (f"training: {len(mods)} modules, {steps} steps ({vids} videos), narration for {written} "
            f"({steps - written} not yet written), {recorded} recorded")


def problems(root: str | Path = DATA) -> List[str]:
    root = Path(root)
    base = root / "training"
    if not base.is_dir():
        return []
    facets = store.load_facets(root)
    out: List[str] = []
    try:
        courses = load(root)
    except (ValueError, yaml.YAMLError) as exc:
        return [f"training: {exc}"]
    for p in sorted(base.iterdir()):
        if p.is_dir() and not (p / "course.yaml").exists():
            out.append(f"training/{p.name}: course.yaml is missing")
    for c in courses:
        cw = f"training/{c['_folder']}/course.yaml"
        if c.get("id") != c["_folder"]:
            out.append(f"{cw}: id '{c.get('id')}' must be the folder name")
        for k in ("name", "short", "description"):
            if not c.get(k):
                out.append(f"{cw}: {k} is blank")
        if not isinstance(c.get("order"), int):
            out.append(f"{cw}: order must be a whole number")
        mods = Path(c["_path"]) / "modules"
        if mods.is_dir():
            for p in sorted(mods.iterdir()):
                if p.is_dir() and not (p / "module.yaml").exists():
                    out.append(f"training/{c['_folder']}/{p.name}: module.yaml is missing")
        orders = [m.get("order") for m in c["modules"]]
        if len(orders) != len(set(map(str, orders))):
            out.append(f"{cw}: two modules share an order number")
        for m in c["modules"]:
            out.extend(module_problems(m, c["_folder"], facets))
    return out


# ---------- the build ----------
class TrainingProblems(Exception):
    pass


def _lesson(c: Dict[str, Any], m: Dict[str, Any], facets: Dict[str, Any], slides: int) -> Dict[str, Any]:
    sec = m["sections"]
    ks = store.bullets(sec.get("Key slides", "")) or [l.strip() for l in sec.get("Key slides", "").splitlines() if l.strip()]
    return {
        "id": m["id"], "event": c["id"], "course": c["id"], "title": m["title"], "order": m["order"],
        "date": None, "start": None, "format": "module", "speakers": [],
        "owner": m.get("owner") or "", "version": m.get("version") or "", "audience": m.get("audience") or "",
        "minutes": m.get("minutes") or 0, "level": LEVELS.get(m.get("level") or "", "Recommended"),
        "categories": m.get("categories") or [], "tags": m.get("tags") or [],
        "ingredients": store.ingredient_groups(m.get("ingredients") or [], facets), "ingredient_words": m.get("ingredients") or [],
        "summary": sec.get("Summary", ""), "takeaways": store.bullets(sec.get("Key learnings", "")),
        "in_practice": sec.get("In practice", ""), "for_us": "", "quotes": [], "detail": sec.get("Detail", ""),
        "key_slides": ks, "quiz": quiz(sec.get("Check your understanding", "")),
        "slides": slides, "slide_source": "deck" if slides else None, "deck_names": [Path(str(m["deck"])).name] if m.get("deck") else [],
        "status": m.get("status") or "draft",
        "sequence": [],
    }


def sequence(m: Dict[str, Any], audio: Dict[tuple, str]) -> List[Dict[str, Any]]:
    """The module's steps in order: each slide, with any video step right after its slide.
    audio maps a step key to its published clip path ('' or missing: no recording)."""
    text = {s["key"]: s for s in (m.get("narration") or {}).get("sections", [])}
    vids = {v["after"]: v for v in videos(m)}
    out = []
    for k in expected_steps(m):
        s = text.get(k) or {}
        v = vids.get(k[1]) if k[0] == "video" else None
        out.append({"kind": k[0], "slide": k[1], "script": s.get("script", ""), "source": (s.get("source") or "").lower(),
                    "audio": audio.get(k, ""),
                    "video": {"id": v["id"], "url": v["url"], "title": v["title"], "channel": v.get("channel") or "", "thumb": v["id"]} if v else None})
    return out


def build_audio(m: Dict[str, Any], dest: Path, published: str) -> Dict[tuple, str]:
    """Convert the module's clips to mono AAC ~48 kbps .m4a in dest (cached by the source's hash; stale files removed).
    Returns {step key: published path} for the steps that exist."""
    by_key = {k: p for k, p in (m.get("clips") or {}).get("by_key", {}).items() if k in set(expected_steps(m))}
    if not by_key:
        if dest.is_dir():
            shutil.rmtree(dest)
        return {}
    if not shutil.which("ffmpeg"):
        raise TrainingProblems("ffmpeg is needed to convert the narration clips (apt-get install ffmpeg / brew install ffmpeg)")
    dest.mkdir(parents=True, exist_ok=True)
    cache_file = dest / "hashes.json"
    try:
        cache = json.loads(cache_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    new_cache, out = {}, {}
    for k, src in sorted(by_key.items()):
        name = _clip_name(k)
        h = hashlib.sha256(src.read_bytes() + AUDIO_SETTINGS.encode()).hexdigest()[:16]
        target = dest / name
        if not (cache.get(name) == h and target.is_file()):
            tmp = dest / (name + ".part.m4a")
            r = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(src), "-vn", "-map_metadata", "-1", "-ac", "1",
                                "-c:a", "aac", "-b:a", "48k", "-movflags", "+faststart", str(tmp)], capture_output=True, text=True)
            if r.returncode != 0:
                tmp.unlink(missing_ok=True)
                raise TrainingProblems(f"{src}: ffmpeg could not convert it: {r.stderr.strip()[:300]}")
            tmp.replace(target)
        new_cache[name] = h
        out[k] = f"{published}/{name}"
    for p in dest.iterdir():
        if p.name != "hashes.json" and p.name not in new_cache:
            p.unlink()
    cache_file.write_text(json.dumps(new_cache, indent=1) + "\n", encoding="utf-8")
    return out


def _video_thumbs(pack: Path, folder: Path, m: Dict[str, Any]) -> None:
    """Add the video steps' thumbnails to the slide pack as data URIs ({"videos": {id: uri}}), rewriting only on change."""
    from PIL import Image
    if not pack.exists():
        return
    d = json.loads(pack.read_text(encoding="utf-8"))
    want: Dict[str, str] = {}
    for v in videos(m):
        f = folder / "files" / f"youtube-{v['id']}.jpg"
        if not f.is_file():
            continue
        img = Image.open(f).convert("RGB")
        if img.width > VIDEO_THUMB_WIDTH:
            img = img.resize((VIDEO_THUMB_WIDTH, round(img.height * VIDEO_THUMB_WIDTH / img.width)), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, "WEBP", quality=70)
        want[v["id"]] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()
    if d.get("videos", {}) != want:
        d["videos"] = want
        pack.write_text(json.dumps(d), encoding="utf-8")


def related(lesson: Dict[str, Any], talks: List[Dict[str, Any]], url: str, most: int = RELATED_MAX) -> List[Dict[str, Any]]:
    """The team library's talks on the same tags: best overlap first, Essential first, newest first; at most `most`."""
    scored = [(team.overlap(lesson, t), t) for t in talks]
    scored = [x for x in scored if x[0]]
    scored.sort(key=lambda x: (x[1].get("date") or ""), reverse=True)
    scored.sort(key=lambda x: (-x[0], team.LEVEL_RANK.get(x[1].get("level"), 1)))
    return [{"title": t["title"], "event": t["_event"], "href": team.site_href(url, f"{t['event']}--{t['id']}"), "level": t.get("level")}
            for _, t in scored[:most]]


def team_talks(path: Path) -> List[Dict[str, Any]]:
    """The team library's talks (team/data/library.json); [] when it has not been built."""
    if not Path(path).exists():
        return []
    lib = json.loads(Path(path).read_text(encoding="utf-8"))
    return [dict(l, _event=c.get("short") or c["name"]) for c in lib.get("courses") or [] for l in c.get("lessons") or []]


def library(courses: List[Dict[str, Any]], root: Path, out: Path, stamp: Dict[str, Any], talks: List[Dict[str, Any]],
            render: bool = True) -> Dict[str, Any]:
    facets = store.load_facets(root)
    url = store.load_sites(root)["team"]
    cs = []
    for c in courses:
        lessons = []
        for m in c["modules"]:
            deck = module_file(Path(m["_path"]), m["deck"])
            pack = out / "build" / "slides" / f"{c['id']}--{m['id']}.json"
            n = team.slide_pack(pack, [deck], True) if render else 0
            if render:
                _video_thumbs(pack, Path(m["_path"]), m)
            name = f"{c['id']}--{m['id']}"
            l = _lesson(c, m, facets, n)
            l["sequence"] = sequence(m, build_audio(m, out / "build" / "audio" / name, f"audio/{name}"))
            l["related"] = related(l, talks, url)
            l["thumb"] = team._thumb(out, {"id": c["id"]}, {"id": m["id"]}, 360) if n else ""
            lessons.append(l)
        if lessons:
            cs.append({"id": c["id"], "name": c["name"], "short": c.get("short") or c["name"], "order": c.get("order"),
                       "description": c.get("description") or "", "start": None, "end": None, "city": None, "lessons": lessons})
    out_facets: Dict[str, List[Dict[str, Any]]] = {}
    for kind in ("categories", "ingredients", "tags"):
        out_facets[kind] = []
        for f in facets.get(kind) or []:
            ls = [f"{c['id']}--{l['id']}" for c in cs for l in c["lessons"] if f["id"] in l[kind]]
            if ls:
                out_facets[kind].append({"id": f["id"], "name": f["name"], "lessons": ls})
    return {"schema": "confnotes.training/1", "built": stamp["date"], "commit": stamp["commit"], "people": [],
            "courses": cs, "facets": out_facets}


def write(out: Path = OUT, root: str | Path = DATA, stamp: Dict[str, Any] | None = None, render: bool = True) -> Dict[str, Any]:
    root = Path(root)
    probs = problems(root)
    if probs:
        raise TrainingProblems("the training library has problems, nothing written:\n" + "\n".join(probs))
    talks = team_talks(out.parent / "team" / "data" / "library.json")
    lib = library(load(root), root, out, stamp or build.git_stamp(), talks, render)
    keep = {f"{c['id']}--{l['id']}.json" for c in lib["courses"] for l in c["lessons"]}
    packs = out / "build" / "slides"
    if packs.is_dir():
        for p in packs.glob("*.json"):
            if p.name not in keep:
                p.unlink()
    audio = out / "build" / "audio"
    if audio.is_dir():
        for p in audio.iterdir():
            if p.is_dir() and f"{p.name}.json" not in keep:
                shutil.rmtree(p)
    (out / "data").mkdir(parents=True, exist_ok=True)
    (out / "data" / "library.json").write_text(json.dumps(lib, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return lib


def files_map(out: Path = OUT) -> Dict[str, Any]:
    """Published path -> local file, for publishing the training site (training/ARTIFACT.md). Narration clips are
    published under audio/<course>--<module>/ as {"from": file, "contentType": "audio/mp4"}."""
    m: Dict[str, Any] = {"app.js": str(out / "app.js"), "styles.css": str(out / "styles.css"), "data/library.json": str(out / "data" / "library.json")}
    lib = json.loads((out / "data" / "library.json").read_text(encoding="utf-8"))
    for c in lib["courses"]:
        for l in c["lessons"]:
            if l["slides"]:
                name = f"{c['id']}--{l['id']}.json"
                m[f"slides/{name}"] = str(out / "build" / "slides" / name)
            for s in l.get("sequence") or []:
                if s.get("audio"):
                    m[s["audio"]] = {"from": str(out / "build" / s["audio"]), "contentType": "audio/mp4"}
    return m
