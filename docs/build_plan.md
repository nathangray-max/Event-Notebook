# Conference Notes: build plan

| Phase | What | State |
|---|---|---|
| 1 | Store, loader and checks (`confnotes/store.py`), text extraction (`extract.py`), the dashboard build and the Suite API export, the dashboard (events, event, session, theme, people, search, to check), the three skills, tests and smoke | **Built 9 Nov 2026** in `nathangray-max/sandbox` under `conference-notes/`, ready to move to its own repo |
| 2 | First real event: Sports & Active Nutrition Summit Europe (London, 9 Nov 2026): Nathan's uploads filed through `add-session`, then `event-report` | next |
| 3 | Publish the dashboard as a private artifact; `ARTIFACT.md` records versions (as ProductDB does) | after phase 2 |
| 4 | Cortex reads the Suite API: a conference's follow-ups offered as tasks on Nathan's word; Market Intelligence reads `themes.json` for its Trend Watch | later, agreed first |
| 5 | Recording import: Otter and Circleback exports converted to `transcript.md` by one command | when a recording exists |

## Moving to its own repo

Suggested name `nathangray-max/conference-notes`, private. From a clone of `sandbox` on the branch that holds this folder:

```sh
git subtree split --prefix=conference-notes -b conference-notes-main
git push git@github.com:nathangray-max/conference-notes.git conference-notes-main:main
```

Nothing inside the folder refers to its place in `sandbox`.
