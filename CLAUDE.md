# Working notes for Conference Notes

Owner: Nathan Gray (Vita Actives, nutraceutical ingredients). This repo is the record of what we learn at conferences (the
Sports & Active Nutrition Summit, Remedy, Vitafoods, FiE): presentations and transcripts as received, a summary and takeaways
per session, themes tracked across events, one report per event, a dashboard and a Suite API. It is its own tool in the
Vita Actives suite beside Cortex, Market Intelligence (`nathangray-max/VA-Analysis`), ProductDB and the Black Book. Cortex
reads it through `exports/api/v1/` (docs/api.md), never its files; this tool reads nothing from Cortex.

## Rules

- **Originals are never changed** (`transcript.md`, `notes.md`, `files/*` as received). Derived text cites passages:
  `[12:40]`, `(slide 7)`, `(notes)`. A takeaway without a passage says "my reading".
- **Nothing is guessed.** A field the sources do not give stays blank and is named in `to_check`.
- **Claude drafts, a person reviews.** `status: reviewed` (and `reviewed_by`) is set only on Nathan's word.
- **Health claims are the speaker's**, reported with the speaker's hedge; never upgraded, never ours.
- **Ids never change**; theme ids are shared across events (`data/themes.yaml`). Add a theme only when none fits.
- **Never hand-edit generated files**: `dashboard/data/`, `exports/api/v1/`, `files/*.txt`. Regenerate.
- **Internal: not for sharing.** Speakers' slides are their copyright.
- **Develop on `main`** of `nathangray-max/Event-Notebook`, this tool's own repo since 10 Nov 2026 (it began as a folder
  of `nathangray-max/sandbox`; the history came with it). Push before a session ends.
- Run `python -m confnotes check` and `python -m pytest -q` before every commit; `node dashboard/test/smoke.mjs` after a
  dashboard change.

## Commands

| Command | Does |
|---|---|
| `python -m confnotes check` | the store's problems and a one-line summary |
| `python -m confnotes extract <event> [<session>]` / `--all` | pull the text out of presentations into `files/<name>.txt` |
| `python -m confnotes build` | `dashboard/data/events.json` (refused while the store has problems) |
| `python -m confnotes api` | `exports/api/v1/*.json` |
| `python -m confnotes all` | check, extract, build, api |
| `python -m confnotes new-event <id> --name ...` / `new-session <event> <id> --title ...` | scaffold a record |
| `python -m pytest -q` · `node dashboard/test/smoke.mjs` | tests · the dashboard in a browser on the synthetic fixture |

## Where to read more

| Task | Read |
|---|---|
| A conference Nathan names | skill `new-event` |
| A presentation, transcript or notes from a talk | skill `add-session` |
| The themes and report of an event | skill `event-report` |
| What the store holds and why, the rules | `docs/design.md` |
| What other tools read | `docs/api.md` |
| What is built next | `docs/build_plan.md` |
| Nathan's decisions | `docs/decisions.csv` |
| Open small findings | `docs/backlog.md` |

## Dashboard

`dashboard/` is static (plain JS, no build, no storage). Its only data is `dashboard/data/events.json`. The smoke test builds
the synthetic fixture (`tests/fixture/`, invented, nothing in it was said by anyone) into a temporary copy, so it never
depends on the real store. Published as a private artifact; how and which versions: `dashboard/ARTIFACT.md`.
