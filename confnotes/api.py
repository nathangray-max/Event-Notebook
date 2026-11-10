"""Suite API v1: exports/api/v1/*.json, what other tools (Cortex first) read (docs/api.md).

`python -m confnotes api` writes the contracts from the store; they are generated and committed, never hand-edited.
Transcripts and the text of slides stay out of the API: a reader that needs them asks for the files.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from confnotes import DATA, ROOT, build, store

OUT = ROOT / "exports" / "api" / "v1"
VERSION = 1

SESSION_KEYS = ["id", "event", "title", "date", "start", "end", "format", "track", "speakers", "themes", "ingredients",
                "relevance", "status", "summary_by", "summary_date", "reviewed_by", "reviewed_date", "attended_by", "links",
                "to_check", "added", "added_by", "has_transcript", "transcript_words", "has_notes", "has_summary"]
EVENT_KEYS = ["id", "name", "short", "start", "end", "city", "country", "venue", "organiser", "url", "status", "attended_by",
              "links", "to_check", "added", "added_by", "description", "has_report"]


def _pick(rec: Dict[str, Any], keys: List[str]) -> Dict[str, Any]:
    return {k: rec.get(k) for k in keys}


def contracts(data: Dict[str, Any], built: str, commit: str) -> Dict[str, Dict[str, Any]]:
    head = {"built": built, "commit": commit}
    events, sessions, takeaways = [], [], []
    for e in data["events"]:
        ev = _pick(e, EVENT_KEYS)
        ev["sessions"] = [s["id"] for s in e["sessions"]]
        ev["themes"] = [{"theme": t.get("theme"), "headline": t.get("headline"), "strength": t.get("strength")} for t in e["themes"]]
        ev["report"] = e["report"] if e["has_report"] else None
        events.append(ev)
        for s in e["sessions"]:
            se = _pick(s, SESSION_KEYS)
            se["summary"] = s["summary"] if s["has_summary"] else None
            se["takeaways"] = s["takeaways"]
            se["quotes"] = s["quotes"]
            se["followups"] = s["followups"]
            se["key_slides"] = s["key_slides"]
            se["detail"] = s["detail"]
            se["files"] = [{"name": f["name"], "kind": f["kind"], "pages": f["pages"]} for f in s["files"]]
            sessions.append(se)
            for i, t in enumerate(s["takeaways"], start=1):
                takeaways.append({"id": f"{e['id']}/{s['id']}#{i}", "event": e["id"], "session": s["id"], "date": s.get("date"),
                                  "text": t["text"], "cites": t["cites"], "themes": s["themes"], "ingredients": s["ingredients"],
                                  "relevance": s.get("relevance"), "status": s.get("status")})
    themes = [dict(t) for t in data["themes"]]
    return {
        "events.json": {"schema": f"confnotes.events/{VERSION}", **head, "count": len(events), "items": events},
        "sessions.json": {"schema": f"confnotes.sessions/{VERSION}", **head, "count": len(sessions), "items": sessions},
        "themes.json": {"schema": f"confnotes.themes/{VERSION}", **head, "count": len(themes), "items": themes},
        "takeaways.json": {"schema": f"confnotes.takeaways/{VERSION}", **head, "count": len(takeaways), "items": takeaways},
    }


def write(out: Path = OUT, root: str | Path = DATA, stamp: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Build the data (refusing on store problems), write the contracts and the manifest.  Returns the manifest."""
    data = build.build(out / ".events.tmp.json", root, stamp)
    (out / ".events.tmp.json").unlink(missing_ok=True)
    g = data["generated"]
    files = contracts(data, g["date"], g["commit"])
    out.mkdir(parents=True, exist_ok=True)
    listing = {}
    for name, body in files.items():
        text = json.dumps(body, indent=1, ensure_ascii=False) + "\n"
        (out / name).write_text(text, encoding="utf-8")
        listing[name] = {"schema": body["schema"], "count": body["count"], "sha256": hashlib.sha256(text.encode()).hexdigest()}
    manifest = {"schema": f"confnotes.manifest/{VERSION}", "built": g["date"], "commit": g["commit"],
                "uncommitted_changes": g["uncommitted_changes"], "contracts": listing,
                "rules": ["Ids never change.", "Absent is null, not zero.", "Takeaways cite their passage in `cites`; one without a cite is a reading.",
                          "Health claims are the speaker's, with the speaker's hedge.", "Internal: not for sharing outside the company."]}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest
