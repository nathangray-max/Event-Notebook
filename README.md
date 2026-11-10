# Conference Notes

Repository: `nathangray-max/Event-Notebook` (private). The tool and its dashboard are called Conference Notes.

Vita Actives' record of **what we learn at conferences**: the presentations and transcripts as received, a summary and the
takeaways of every session, the themes running through an event and across years, and one report per event. Part of the
Vita Actives tool suite beside Cortex (meetings, projects, tasks), Market Intelligence (`nathangray-max/VA-Analysis`),
ProductDB and the Black Book. Cortex reads it through the Suite API (`exports/api/v1/`).

- `data/events/<event-id>/`: one folder per event (`event.yaml`, `themes.yaml`, `report.md`, `sessions/<session-id>/` with
  `session.yaml`, `transcript.md`, `notes.md`, `summary.md`, `files/`). `data/themes.yaml`: the theme vocabulary.
- `confnotes/`: the loader and checks (`store.py`), text extraction from PDF, PPTX and DOCX (`extract.py`), the dashboard
  build (`build.py`), the Suite API export (`api.py`) and the command line (`python -m confnotes`).
- `.claude/skills/`: how material becomes a record: `new-event`, `add-session`, `event-report`.
- `docs/design.md`: what it holds and why. `docs/api.md`: the contracts. `docs/build_plan.md`: phases.

Filing a talk: drop the slides, the transcript or your notes into a Claude session and say which talk and which event it was.
Claude files the originals untouched, pulls the text out of the slides, drafts the summary with every takeaway citing its
passage, proposes themes, and asks you to say "reviewed" once you have read it.

## Dashboard

A static site in `dashboard/` (plain JS, no build step): events, one page per event (sessions by day, themes with evidence, the
report), one page per session (summary, cited takeaways, quotes, the slides' text slide by slide, the transcript and notes),
one page per theme (its history across events), people, a search over everything including slide text and transcripts,
and a "To check" list. Its only data is `dashboard/data/events.json`, written by `python -m confnotes build` from the store
(only when `python -m confnotes check` finds no problems), stamped with the commit and date. Never edit the JSON by hand.

- Build: `python -m confnotes all`
- Test: `python -m pytest -q`, then `node dashboard/test/smoke.mjs` (builds the synthetic fixture into a temporary copy of
  the dashboard, visits every view at 1280 and 390 wide, checks counts, cites, originals, search and sideways overflow;
  screenshots go to `$SHOTS`).
- View locally: `python -m http.server -d dashboard` and open `http://localhost:8000/`.

Needs Python 3.11+ with `pyyaml`, `pypdf`, `python-pptx`, `python-docx` and `pytest`; Node 20+ with Playwright for the smoke test.
