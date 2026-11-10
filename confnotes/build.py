"""Build the dashboard data: dashboard/data/events.json from the store (docs/design.md §4).

`python -m confnotes build` reads the store through store.load() only, refuses to write while store.problems() is not
empty, and stamps the file with the git commit and the date.  The dashboard reads nothing else.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Dict, List

from confnotes import DATA, ROOT, store

OUT = ROOT / "dashboard" / "data" / "events.json"

# where a takeaway or quote says it comes from: [12:40], [1:02:10], (slide 7), (page 3), (notes)
CITE_RE = re.compile(r"\[(\d{1,2}:\d{2}(?::\d{2})?)\]|\((slide|page|section|photo) (\d+)\)|\((notes|otter)\)", re.I)


class StoreProblems(Exception):
    """The store has problems, so nothing is built."""


def cites(text: str) -> List[str]:
    """The sources a line names, as written: ['12:40', 'slide 7', 'notes']."""
    out = []
    for m in CITE_RE.finditer(text):
        if m.group(1):
            out.append(m.group(1))
        elif m.group(2):
            out.append(f"{m.group(2).lower()} {m.group(3)}")
        else:
            out.append(m.group(4).lower())
    return out


def git_stamp() -> Dict[str, Any]:
    def git(*a: str) -> str:
        return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    try:
        commit = git("rev-parse", "--short", "HEAD")
        dirty = bool(git("status", "--porcelain", "--", str(DATA), str(ROOT / "confnotes")))
    except (OSError, subprocess.CalledProcessError):
        commit, dirty = "unknown", False
    return {"commit": commit, "uncommitted_changes": dirty, "date": dt.date.today().isoformat()}


def _public(rec: Dict[str, Any], drop: tuple = ()) -> Dict[str, Any]:
    return {k: v for k, v in rec.items() if not k.startswith("_") and k not in drop}


def session_record(s: Dict[str, Any], event_id: str) -> Dict[str, Any]:
    out = _public(s, drop=("summary_md",))
    out["event"] = event_id
    out["speakers"] = [sp if isinstance(sp, dict) else {"name": str(sp)} for sp in (s.get("speakers") or [])]
    out["themes"] = list(s.get("themes") or [])
    out["ingredients"] = list(s.get("ingredients") or [])
    out["attended_by"] = list(s.get("attended_by") or [])
    out["links"] = dict(s.get("links") or {})
    out["to_check"] = (s.get("to_check") or "").strip()
    summ = s.get("summary") or {}
    out["summary"] = {h: summ.get(h, "") for h in store.SUMMARY_HEADINGS + store.OPTIONAL_SUMMARY_HEADINGS}
    photos = store.photo_index(s["files"])
    out["photos"] = {str(n): name for n, name in sorted(photos.items())}
    out["key_slides"] = []
    for b in store.bullets(summ.get("Key slides", "")):
        m = store.KEY_SLIDE_RE.match(b)
        if m and int(m.group(1)) in photos:
            out["key_slides"].append({"photo": int(m.group(1)), "file": photos[int(m.group(1))], "caption": m.group(2).strip()})
    out["detail"] = [{"text": t, "cites": cites(t)} for t in store.bullets(summ.get("Detail", ""))]
    out["takeaways"] = [{"text": t, "cites": cites(t)} for t in store.bullets(summ.get("Key takeaways", ""))]
    out["quotes"] = [{"text": t, "cites": cites(t)} for t in store.bullets(summ.get("Quotes", ""))]
    out["followups"] = store.bullets(summ.get("Follow-ups", ""))
    out["transcript_words"] = len(s["transcript"].split()) if s["transcript"] else 0
    out["has_transcript"] = bool(s["transcript"])
    out["has_notes"] = bool(s["notes"])
    out["has_summary"] = bool(s.get("summary_md"))
    for k in ("date", "start", "end", "added", "summary_date", "reviewed_date"):
        if out.get(k) is not None:
            out[k] = str(out[k])
    return out


def event_record(e: Dict[str, Any]) -> Dict[str, Any]:
    out = _public(e, drop=("report_md",))
    out["attended_by"] = list(e.get("attended_by") or [])
    out["links"] = dict(e.get("links") or {})
    out["to_check"] = (e.get("to_check") or "").strip()
    out["report"] = {h: (e.get("report") or {}).get(h, "") for h in store.REPORT_HEADINGS}
    out["report_md"] = e.get("report_md") or ""
    out["has_report"] = bool(e.get("report_md"))
    out["themes"] = [dict(t, evidence=list(t.get("evidence") or [])) for t in e.get("themes") or []]
    out["sessions"] = sorted((session_record(s, e["id"]) for s in e["sessions"]),
                             key=lambda s: (s.get("date") or "", s.get("start") or "", s.get("title") or ""))
    for k in ("start", "end", "added"):
        if out.get(k) is not None:
            out[k] = str(out[k])
    return out


def theme_records(st: Dict[str, Any], events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Every theme of the vocabulary with the events that carried it (their headline and evidence) and its sessions."""
    out = []
    for t in st["themes"]:
        rec = dict(t)
        rec["events"] = []
        rec["sessions"] = []
        for e in events:
            for et in e["themes"]:
                if et.get("theme") == t["id"]:
                    rec["events"].append({"event": e["id"], "event_name": e.get("name"), "start": e.get("start"),
                                          "headline": et.get("headline"), "strength": et.get("strength"),
                                          "evidence": et.get("evidence") or []})
            for s in e["sessions"]:
                if t["id"] in s["themes"]:
                    rec["sessions"].append({"event": e["id"], "session": s["id"], "title": s["title"], "date": s.get("date")})
        rec["events"].sort(key=lambda x: x.get("start") or "")
        out.append(rec)
    return out


def build(out: Path = OUT, root: str | Path = DATA, stamp: Dict[str, Any] | None = None) -> Dict[str, Any]:
    probs = store.problems(root)
    if probs:
        raise StoreProblems("store has problems, nothing built:\n" + "\n".join(probs))
    st = store.load(root)
    events = sorted((event_record(e) for e in st["events"]), key=lambda e: e.get("start") or "", reverse=True)
    data = {"generated": stamp or git_stamp(), "events": events, "themes": theme_records(st, events)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return data
