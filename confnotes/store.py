"""The store: data/themes.yaml and data/events/<event>/... (docs/design.md §2).

This module is the one loader and the checks.  Nothing else reads the files directly.

    load(root)      -> {"themes": [...], "events": [...]} with every session's yaml, summary parts, transcript, notes, files
    problems(root)  -> what is wrong (ids, required fields, allowed values, dates, theme ids, summary headings); [] when clean
    summary(store)  -> one line

`python -m confnotes check` prints the problems and the summary.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import yaml

from confnotes import DATA

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")

FORMATS = {"keynote", "talk", "panel", "workshop", "fireside", "breakout", "pitch", "roundtable", "exhibition", "other"}
SESSION_STATUS = {"captured", "summarised", "reviewed"}
EVENT_STATUS = {"planned", "attending", "attended", "reported"}
RELEVANCE = {"high", "medium", "low"}
STRENGTH = {"dominant", "present", "emerging"}

EVENT_REQUIRED = ["id", "name", "status", "added"]
SESSION_REQUIRED = ["id", "title", "status", "added"]
THEME_REQUIRED = ["id", "name"]

# summary.md headings, in order; the build reads each part by heading
SUMMARY_HEADINGS = ["Summary", "Key takeaways", "For Vita Actives", "Quotes", "Follow-ups"]
# optional headings: slides that carry the argument, and everything else worth keeping (Nathan, 10 Nov 2026)
OPTIONAL_SUMMARY_HEADINGS = ["Key slides", "Detail"]
SUMMARY_MAX_WORDS = 220        # the Summary section reads as prose, not a list of figures
TAKEAWAYS_MAX = 6
KEY_SLIDES_MAX = 4
CITE_IN_PROSE = re.compile(r"\[\d{1,2}:\d{2}(?::\d{2})?\]|\((?:slide|page|section|photo) \d+\)|\((?:notes|otter)\)")
KEY_SLIDE_RE = re.compile(r"^\(photo (\d+)\)\s*(.+)$")
REPORT_HEADINGS = ["In brief", "Themes", "Sessions that mattered", "People met", "For Vita Actives", "Follow-ups", "Sources"]

PHOTO_MARK = re.compile(r"^--- photo (\d+) ---$", re.M)
PAGE_MARK = re.compile(r"^--- (?:slide|page|section|photo) \d+ ---$", re.M)
FILE_KINDS = {".pdf": "pdf", ".pptx": "pptx", ".docx": "docx", ".txt": "text", ".md": "text",
              ".jpg": "photo", ".jpeg": "photo", ".png": "photo", ".webp": "photo", ".heic": "photo"}


def _yaml(path: Path) -> Dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        d = yaml.safe_load(f) or {}
    if not isinstance(d, dict):
        raise ValueError(f"{path}: expected a mapping")
    return d


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def split_sections(md: str) -> Dict[str, str]:
    """A markdown document's `## ` sections by heading (text before the first `## ` under '').  Headings as written."""
    out: Dict[str, str] = {}
    cur, buf = "", []
    for line in md.splitlines():
        if line.startswith("## "):
            out[cur] = "\n".join(buf).strip()
            cur, buf = line[3:].strip(), []
        else:
            buf.append(line)
    out[cur] = "\n".join(buf).strip()
    return out


def bullets(text: str) -> List[str]:
    """The `- ` items of a section, each one string (continuation lines joined)."""
    items: List[str] = []
    for line in text.splitlines():
        if re.match(r"^\s*[-*] ", line):
            items.append(re.sub(r"^\s*[-*] ", "", line).strip())
        elif items and line.strip() and not line.startswith("#"):
            items[-1] += " " + line.strip()
    return items


def _files(folder: Path) -> List[Dict[str, Any]]:
    """The originals in a session's files/ folder, each with the text pulled out of it (`<name>.txt`, from `extract`)."""
    out = []
    if not folder.is_dir():
        return out
    names = {p.name for p in folder.iterdir()}
    for p in sorted(folder.iterdir()):
        if p.name.startswith(".") or not p.is_file():
            continue
        if p.suffix.lower() == ".txt" and p.name[:-4] in names:
            continue  # the extracted text of another file: read with that file
        kind = FILE_KINDS.get(p.suffix.lower(), "other")
        rec: Dict[str, Any] = {"name": p.name, "kind": kind, "bytes": p.stat().st_size, "text": None, "pages": None, "photos": []}
        if kind == "text":
            rec["text"] = _text(p)
        elif (folder / (p.name + ".txt")).exists():
            rec["text"] = _text(folder / (p.name + ".txt"))
            rec["pages"] = len(PAGE_MARK.findall(rec["text"])) or None
            if kind == "photo":
                rec["photos"] = [int(n) for n in PHOTO_MARK.findall(rec["text"])]
        out.append(rec)
    return out


def photo_index(files: List[Dict[str, Any]]) -> Dict[int, str]:
    """Photo number -> file name, from the `--- photo N ---` marker in each photo's transcribed text."""
    out: Dict[int, str] = {}
    for f in files:
        for n in f.get("photos") or []:
            out.setdefault(n, f["name"])
    return out


def summary_problems(where: str, sections: Dict[str, str], photos: Dict[int, str]) -> List[str]:
    """The summary format (docs/design.md, "Summary"): prose Summary, few takeaways, key slides that exist."""
    out: List[str] = []
    summ = sections.get("Summary", "")
    words = len(summ.split())
    if words > SUMMARY_MAX_WORDS:
        out.append(f"{where}/summary.md: Summary is {words} words; keep it under {SUMMARY_MAX_WORDS} and move figures to Detail")
    if CITE_IN_PROSE.search(summ):
        out.append(f"{where}/summary.md: Summary carries cites; it is prose, the cites belong in Key takeaways and Detail")
    n = len(bullets(sections.get("Key takeaways", "")))
    if n > TAKEAWAYS_MAX:
        out.append(f"{where}/summary.md: {n} key takeaways; keep at most {TAKEAWAYS_MAX} and move the rest to Detail")
    if "Key slides" in sections:
        slides = bullets(sections["Key slides"])
        if len(slides) > KEY_SLIDES_MAX:
            out.append(f"{where}/summary.md: {len(slides)} key slides; keep at most {KEY_SLIDES_MAX}")
        for b in slides:
            m = KEY_SLIDE_RE.match(b)
            if not m:
                out.append(f"{where}/summary.md: key slide '{b[:40]}' must start '(photo N)' then a caption")
            elif int(m.group(1)) not in photos:
                out.append(f"{where}/summary.md: key slide photo {m.group(1)} is not among this session's photos")
    return out


def load_session(folder: Path) -> Dict[str, Any]:
    s = _yaml(folder / "session.yaml")
    s["_path"] = str(folder)
    s["transcript"] = _text(folder / "transcript.md")
    s["notes"] = _text(folder / "notes.md")
    s["summary_md"] = _text(folder / "summary.md")
    s["summary"] = split_sections(s["summary_md"]) if s["summary_md"] else {}
    s["files"] = _files(folder / "files")
    return s


def load_event(folder: Path) -> Dict[str, Any]:
    e = _yaml(folder / "event.yaml")
    e["_path"] = str(folder)
    th = _yaml(folder / "themes.yaml") if (folder / "themes.yaml").exists() else {}
    e["themes"] = th.get("themes") or []
    e["report_md"] = _text(folder / "report.md")
    e["report"] = split_sections(e["report_md"]) if e["report_md"] else {}
    sessions = folder / "sessions"
    e["sessions"] = [load_session(p) for p in sorted(sessions.iterdir()) if (p / "session.yaml").exists()] if sessions.is_dir() else []
    return e


def load(root: str | Path = DATA) -> Dict[str, Any]:
    root = Path(root)
    themes = _yaml(root / "themes.yaml").get("themes") or [] if (root / "themes.yaml").exists() else []
    events_dir = root / "events"
    events = [load_event(p) for p in sorted(events_dir.iterdir()) if (p / "event.yaml").exists()] if events_dir.is_dir() else []
    return {"themes": themes, "events": events}


def _req(out: List[str], where: str, rec: Dict[str, Any], fields: List[str]) -> None:
    for f in fields:
        if rec.get(f) in (None, "", []):
            out.append(f"{where}: {f} is blank")


def _date(out: List[str], where: str, rec: Dict[str, Any], *fields: str) -> None:
    for f in fields:
        v = rec.get(f)
        if v not in (None, "") and not DATE_RE.match(str(v)):
            out.append(f"{where}: {f} '{v}' is not YYYY-MM-DD")


def _allowed(out: List[str], where: str, rec: Dict[str, Any], field: str, allowed: set) -> None:
    v = rec.get(field)
    if v not in (None, "") and v not in allowed:
        out.append(f"{where}: {field} '{v}' not in {sorted(allowed)}")


def problems(root: str | Path = DATA) -> List[str]:
    """What is wrong with the store.  Empty when clean."""
    out: List[str] = []
    try:
        store = load(root)
    except Exception as e:  # a yaml that does not parse stops everything else
        return [f"cannot load: {e}"]
    theme_ids = set()
    for t in store["themes"]:
        where = f"themes.yaml ({t.get('id') or 'no id'})"
        _req(out, where, t, THEME_REQUIRED)
        if t.get("id") in theme_ids:
            out.append(f"{where}: duplicate id")
        theme_ids.add(t.get("id"))
        if t.get("id") and not ID_RE.match(str(t["id"])):
            out.append(f"{where}: id must be lower-case words joined by hyphens")
    event_ids = set()
    session_ids = set()
    for e in store["events"]:
        folder = Path(e["_path"]).name
        where = f"events/{folder}"
        _req(out, where, e, EVENT_REQUIRED)
        if e.get("id") and e["id"] != folder:
            out.append(f"{where}: id '{e['id']}' differs from its folder name")
        if e.get("id") in event_ids:
            out.append(f"{where}: duplicate event id")
        event_ids.add(e.get("id"))
        if e.get("id") and not ID_RE.match(str(e["id"])):
            out.append(f"{where}: id must be lower-case words joined by hyphens")
        _date(out, where, e, "start", "end", "added")
        _allowed(out, where, e, "status", EVENT_STATUS)
        if e.get("start") and e.get("end") and str(e["end"]) < str(e["start"]):
            out.append(f"{where}: end before start")
        local = set()
        for i, t in enumerate(e["themes"]):
            tw = f"{where}/themes.yaml #{i + 1}"
            if not t.get("theme"):
                out.append(f"{tw}: theme is blank")
            elif t["theme"] not in theme_ids:
                out.append(f"{tw}: theme '{t['theme']}' is not in data/themes.yaml")
            if t.get("theme") in local:
                out.append(f"{tw}: theme '{t['theme']}' listed twice")
            local.add(t.get("theme"))
            if not t.get("headline"):
                out.append(f"{tw}: headline is blank")
            _allowed(out, tw, t, "strength", STRENGTH)
            for ev in t.get("evidence") or []:
                if ev.get("session") and ev["session"] not in {s.get("id") for s in e["sessions"]}:
                    out.append(f"{tw}: evidence names session '{ev['session']}', not in this event")
                if not ev.get("quote"):
                    out.append(f"{tw}: an evidence item has no quote")
        if e["report_md"]:
            missing = [h for h in REPORT_HEADINGS if h not in e["report"]]
            if missing:
                out.append(f"{where}/report.md: missing headings {missing}")
            if e.get("status") != "reported":
                out.append(f"{where}: has a report but status is '{e.get('status')}', not 'reported'")
        elif e.get("status") == "reported":
            out.append(f"{where}: status 'reported' but no report.md")
        for s in e["sessions"]:
            sf = Path(s["_path"]).name
            sw = f"{where}/sessions/{sf}"
            _req(out, sw, s, SESSION_REQUIRED)
            if s.get("id") and s["id"] != sf:
                out.append(f"{sw}: id '{s['id']}' differs from its folder name")
            key = (e.get("id"), s.get("id"))
            if key in session_ids:
                out.append(f"{sw}: duplicate session id")
            session_ids.add(key)
            if s.get("id") and not ID_RE.match(str(s["id"])):
                out.append(f"{sw}: id must be lower-case words joined by hyphens")
            _date(out, sw, s, "date", "added", "summary_date", "reviewed_date")
            for f in ("start", "end"):
                if s.get(f) not in (None, "") and not TIME_RE.match(str(s[f])):
                    out.append(f"{sw}: {f} '{s[f]}' is not HH:MM")
            _allowed(out, sw, s, "format", FORMATS)
            _allowed(out, sw, s, "status", SESSION_STATUS)
            _allowed(out, sw, s, "relevance", RELEVANCE)
            for f in ("themes", "ingredients", "attended_by"):
                v = s.get(f)
                if v not in (None, "") and (not isinstance(v, list) or not all(isinstance(x, str) for x in v)):
                    out.append(f"{sw}: {f} must be a list of strings (quote a name with a colon, e.g. \"IsoClr: Pea\")")
            for t in s.get("themes") or []:
                if isinstance(t, str) and t not in theme_ids:
                    out.append(f"{sw}: theme '{t}' is not in data/themes.yaml")
            for sp in s.get("speakers") or []:
                if not isinstance(sp, dict) or not sp.get("name"):
                    out.append(f"{sw}: a speaker has no name")
            has_original = bool(s["transcript"] or s["notes"] or s["files"])
            if not has_original and s.get("status") in ("summarised", "reviewed"):
                out.append(f"{sw}: status '{s['status']}' but no transcript, notes or files to summarise from")
            if s["summary_md"]:
                missing = [h for h in SUMMARY_HEADINGS if h not in s["summary"]]
                if missing:
                    out.append(f"{sw}/summary.md: missing headings {missing}")
                if not s["summary_md"].lstrip().startswith("# "):
                    out.append(f"{sw}/summary.md: must start with '# <title>'")
                out.extend(summary_problems(sw, s["summary"], photo_index(s["files"])))
                if s.get("status") == "captured":
                    out.append(f"{sw}: has a summary but status is 'captured'")
                if not s.get("summary_by"):
                    out.append(f"{sw}: has a summary but summary_by is blank")
            elif s.get("status") in ("summarised", "reviewed"):
                out.append(f"{sw}: status '{s['status']}' but no summary.md")
            if s.get("status") == "reviewed" and not (s.get("reviewed_by") and s.get("reviewed_date")):
                out.append(f"{sw}: reviewed needs reviewed_by and reviewed_date")
            if s.get("reviewed_by") and s.get("status") != "reviewed":
                out.append(f"{sw}: reviewed_by set but status is '{s.get('status')}'")
    return out


def summary(store: Dict[str, Any]) -> str:
    events = store["events"]
    sessions = [s for e in events for s in e["sessions"]]
    by = {k: sum(1 for s in sessions if s.get("status") == k) for k in ("captured", "summarised", "reviewed")}
    files = sum(len(s["files"]) for s in sessions)
    transcripts = sum(1 for s in sessions if s["transcript"])
    open_ = sum(1 for e in events if (e.get("to_check") or "").strip()) + sum(1 for s in sessions if (s.get("to_check") or "").strip())
    reported = sum(1 for e in events if e["report_md"])
    return (f"{len(events)} events ({reported} reported), {len(sessions)} sessions "
            f"({by['captured']} captured, {by['summarised']} summarised, {by['reviewed']} reviewed), "
            f"{files} files, {transcripts} transcripts, {len(store['themes'])} themes, {open_} things to check")
