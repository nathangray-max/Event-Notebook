# Conference Notes: build plan

| Phase | What | State |
|---|---|---|
| 1 | Store, loader and checks (`confnotes/store.py`), text extraction (`extract.py`), the dashboard build and the Suite API export, the dashboard (events, event, session, theme, people, search, to check), the three skills, tests and smoke | **Built 9 Nov 2026** in `nathangray-max/sandbox` under `conference-notes/`; moved to `nathangray-max/Event-Notebook` on 10 Nov 2026 |
| 2 | First real event: Sports & Active Nutrition Summit Europe (London, 9 Nov 2026): Nathan's uploads filed through `add-session`, then `event-report` | next |
| 3 | Publish the dashboard as a private artifact; `ARTIFACT.md` records versions (as ProductDB does) | **Version 1 published 10 Nov 2026** |
| 3b | **Cross-show roundup** after FiE 2026 (Nathan, 17 Nov): potential partners, potential strategic acquisitions and activity across Remedy CDMO, SANS Europe, the Healthspan Summit and FiE, from the session summaries and `data/leads.yaml` | drafted 20 Nov 2026 as a Claude doc, https://claude.ai/artifact/VCt4qYHQV9wPWZx7odCt2L (confidential); awaiting Nathan's review |
| 3c | **Team library** (`team/`): a separate, simpler site for Nathan's team, without confidential sessions or leads; field-guide talk pages, browsing by ingredient, market category and insight type (`data/facets.yaml`) | **Built 24 Nov 2026**, published privately (team/ARTIFACT.md); AI assistant parked (decisions.csv) |
| 4 | Cortex reads the Suite API: a conference's follow-ups offered as tasks on Nathan's word; Market Intelligence reads `themes.json` for its Trend Watch | later, agreed first |
| 5 | Recording import: Otter and Circleback exports converted to `transcript.md` by one command | when a recording exists |
| 6 | **Session audio (parked, Nathan 24 Nov 2026)**: Otter audio exports trimmed to each session's range (no breaks or side talk), compressed mono, stored as artifact assets outside git; a player beside the slides, every [mm:ss] cite jumps to it. Admin dashboard first; the team library only on Nathan's word (organisers' terms on recordings). Also a candidate for an internal staff-training version of the library. Never for confidential sessions | when Nathan revives it |

## Its own repo (done 10 Nov 2026)

The tool moved from the `conference-notes/` folder of `nathangray-max/sandbox` to `nathangray-max/Event-Notebook`, with its
history (`git subtree split --prefix=conference-notes`, pushed to `main`). Work continues on `main` here. The sandbox copy
is frozen and points here.
