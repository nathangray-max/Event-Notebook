# Conference Notes: build plan

| Phase | What | State |
|---|---|---|
| 1 | Store, loader and checks (`confnotes/store.py`), text extraction (`extract.py`), the dashboard build and the Suite API export, the dashboard (events, event, session, theme, people, search, to check), the three skills, tests and smoke | **Built 9 Nov 2026** in `nathangray-max/sandbox` under `conference-notes/`; moved to `nathangray-max/Event-Notebook` on 10 Nov 2026 |
| 2 | First real event: Sports & Active Nutrition Summit Europe (London, 9 Nov 2026): Nathan's uploads filed through `add-session`, then `event-report` | next |
| 3 | Publish the dashboard as a private artifact; `ARTIFACT.md` records versions (as ProductDB does) | **Version 1 published 10 Nov 2026** |
| 4 | Cortex reads the Suite API: a conference's follow-ups offered as tasks on Nathan's word; Market Intelligence reads `themes.json` for its Trend Watch | later, agreed first |
| 5 | Recording import: Otter and Circleback exports converted to `transcript.md` by one command | when a recording exists |

## Its own repo (done 10 Nov 2026)

The tool moved from the `conference-notes/` folder of `nathangray-max/sandbox` to `nathangray-max/Event-Notebook`, with its
history (`git subtree split --prefix=conference-notes`, pushed to `main`). Work continues on `main` here. The sandbox copy
is frozen and points here.
