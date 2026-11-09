"""The command line: python -m confnotes <command>.

    check                                   the store's problems and a summary (exit 1 when there are problems)
    extract <event> [<session>] | --all     pull the text out of the presentations in files/
    photos <event> <session>                file photos of slides small (WebP, 1600 px)
    build                                   dashboard/data/events.json
    api                                     exports/api/v1/*.json
    all                                     check, extract --all, build, api
    new-event <event-id> --name "..." [--start YYYY-MM-DD --end YYYY-MM-DD --city ... --organiser ... --url ...]
    new-session <event-id> <session-id> --title "..." [--date --start --end --format --track]
"""
from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

import yaml

from confnotes import DATA, ROOT, api, build, extract, photos, store


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _dump(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=120), encoding="utf-8")


def cmd_check(_a) -> int:
    probs = store.problems()
    for p in probs:
        print(p)
    print(store.summary(store.load()))
    return 1 if probs else 0


def cmd_extract(a) -> int:
    events = DATA / "events"
    folders = []
    if a.all:
        folders = [s for e in sorted(events.iterdir()) for s in sorted((e / "sessions").iterdir()) if (e / "sessions").is_dir()] if events.is_dir() else []
    else:
        if not a.event:
            print("name an event, or --all"); return 2
        base = events / a.event / "sessions"
        if not base.is_dir():
            print(f"no sessions folder for event '{a.event}'"); return 2
        folders = [base / a.session] if a.session else sorted(base.iterdir())
    n = 0
    for f in folders:
        if not (f / "session.yaml").exists():
            continue
        done = extract.extract_session(f)
        for name, pages in done.items():
            print(f"{f.parent.parent.name}/{f.name}: {name} -> {name}.txt ({pages} pages)")
            n += 1
    print(f"{n} files extracted")
    return 0


def cmd_photos(a) -> int:
    folder = DATA / "events" / a.event / "sessions" / a.session
    if not (folder / "session.yaml").exists():
        print(f"no session {a.event}/{a.session}"); return 2
    done = photos.reduce_photos(folder)
    for old, new in done.items():
        print(f"{old} -> {new}")
    print(f"{len(done)} photos reduced")
    return 0


def cmd_build(_a) -> int:
    try:
        d = build.build()
    except build.StoreProblems as e:
        print(e); return 1
    g = d["generated"]
    ns = sum(len(e["sessions"]) for e in d["events"])
    print(f"wrote {build.OUT.relative_to(ROOT)}: {len(d['events'])} events, {ns} sessions, {len(d['themes'])} themes, commit {g['commit']}, {g['date']}")
    return 0


def cmd_api(_a) -> int:
    try:
        m = api.write()
    except build.StoreProblems as e:
        print(e); return 1
    for name, c in m["contracts"].items():
        print(f"wrote exports/api/v1/{name}: {c['schema']}, {c['count']} items")
    return 0


def cmd_all(a) -> int:
    rc = cmd_check(a)
    if rc:
        return rc
    a.all, a.event, a.session = True, None, None
    cmd_extract(a)
    return cmd_build(a) or cmd_api(a)


def cmd_new_event(a) -> int:
    folder = DATA / "events" / a.event
    if (folder / "event.yaml").exists():
        print(f"{folder / 'event.yaml'} exists; edit it instead"); return 1
    today = dt.date.today().isoformat()
    _dump(folder / "event.yaml", {
        "id": a.event, "name": a.name, "short": a.short or "", "start": a.start or "", "end": a.end or a.start or "",
        "city": a.city or "", "country": a.country or "", "venue": a.venue or "", "organiser": a.organiser or "", "url": a.url or "",
        "status": a.status, "attended_by": [], "links": {}, "description": "",
        "to_check": a.to_check or "Dates, venue and who attended still to confirm.", "added": today, "added_by": a.by,
    })
    (folder / "sessions").mkdir(exist_ok=True)
    print(f"created {_rel(folder)}/event.yaml")
    return 0


def cmd_new_session(a) -> int:
    folder = DATA / "events" / a.event / "sessions" / a.session
    if not (DATA / "events" / a.event / "event.yaml").exists():
        print(f"no event '{a.event}'; run new-event first"); return 1
    if (folder / "session.yaml").exists():
        print(f"{folder / 'session.yaml'} exists; edit it instead"); return 1
    today = dt.date.today().isoformat()
    _dump(folder / "session.yaml", {
        "id": a.session, "title": a.title, "date": a.date or "", "start": a.start or "", "end": a.end or "",
        "format": a.format or "talk", "track": a.track or "", "speakers": [], "themes": [], "ingredients": [],
        "relevance": "", "status": "captured", "summary_by": "", "summary_date": "", "reviewed_by": "", "reviewed_date": "",
        "attended_by": [], "links": {}, "to_check": a.to_check or "Speakers, time and track still to confirm from the programme.",
        "added": today, "added_by": a.by,
    })
    (folder / "files").mkdir(exist_ok=True)
    print(f"created {_rel(folder)}/session.yaml (drop originals in files/, transcript.md, notes.md)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m confnotes", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check").set_defaults(fn=cmd_check)
    x = sub.add_parser("extract"); x.add_argument("event", nargs="?"); x.add_argument("session", nargs="?"); x.add_argument("--all", action="store_true"); x.set_defaults(fn=cmd_extract)
    ph = sub.add_parser("photos"); ph.add_argument("event"); ph.add_argument("session"); ph.set_defaults(fn=cmd_photos)
    sub.add_parser("build").set_defaults(fn=cmd_build)
    sub.add_parser("api").set_defaults(fn=cmd_api)
    sub.add_parser("all").set_defaults(fn=cmd_all)
    ne = sub.add_parser("new-event"); ne.add_argument("event"); ne.add_argument("--name", required=True)
    for f in ("short", "start", "end", "city", "country", "venue", "organiser", "url", "to-check"):
        ne.add_argument("--" + f)
    ne.add_argument("--status", default="attending", choices=sorted(store.EVENT_STATUS)); ne.add_argument("--by", default="Nathan"); ne.set_defaults(fn=cmd_new_event)
    ns = sub.add_parser("new-session"); ns.add_argument("event"); ns.add_argument("session"); ns.add_argument("--title", required=True)
    for f in ("date", "start", "end", "track", "to-check"):
        ns.add_argument("--" + f)
    ns.add_argument("--format", choices=sorted(store.FORMATS)); ns.add_argument("--by", default="Nathan"); ns.set_defaults(fn=cmd_new_session)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
