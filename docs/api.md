# Suite API v1: what Conference Notes publishes for other tools

Cortex and any agent read Conference Notes through the versioned files in `exports/api/v1/`, never through the dashboard
bundle (`dashboard/data/events.json`), whose keys follow the pages. `python -m confnotes api` writes them; they are generated
and committed, never edited by hand.

| File | Schema | Items | What an item holds |
|---|---|---|---|
| `manifest.json` | `confnotes.manifest/1` | | build date, source commit, each contract's schema, count and SHA-256, the rules |
| `events.json` | `confnotes.events/1` | events, newest first | id, name, short, start, end, city, country, venue, organiser, url, status (`planned`, `attending`, `attended`, `reported`), attended_by, links, to_check, description, `sessions` (ids), `themes` (theme id, headline, strength), `report` (the sections by heading, or null) |
| `sessions.json` | `confnotes.sessions/1` | sessions, by event then time | id, event, title, date, start, end, format, track, speakers (name, organisation, role), themes (ids), ingredients, relevance, status (`captured`, `summarised`, `reviewed`), summary_by, summary_date, reviewed_by, reviewed_date, attended_by, links, to_check, `summary` (sections by heading, or null), `takeaways` and `quotes` (text and `cites`), `followups`, `files` (name, kind, pages), has_transcript, transcript_words, has_notes |
| `themes.json` | `confnotes.themes/1` | the vocabulary | id, name, description, first_seen, `events` (event, headline, strength, evidence quotes with session and where), `sessions` (event, session, title, date) |
| `takeaways.json` | `confnotes.takeaways/1` | every takeaway, flat | id (`<event>/<session>#n`), event, session, date, text, cites, themes, ingredients, relevance, status |

Every file starts with `schema`, `built` (date) and `commit`.

## Rules

- **Ids never change.** Event and session ids are their folder names; theme ids are shared across events. Store ids, not names.
- **Absent is null, not zero.** A field the sources did not give is null or blank, and named in `to_check`.
- **Cites.** A takeaway's `cites` lists the passages it rests on, as written: `"12:40"` (time in the transcript), `"slide 7"`,
  `"page 3"`, `"notes"`. An empty list means a reading, not a fact from the talk; a reader shows it as such.
- **Status.** Only `reviewed` sessions have been read by a person. A tool that shows takeaways to anyone but Nathan should
  take `reviewed` ones only.
- **Hedges.** Health claims and figures are the speaker's, with the speaker's own hedge. Never upgrade one.
- **Transcripts and slide text stay out of the API.** They are in the repo (`data/events/.../sessions/...`); a reader that needs
  them reads the files. The dashboard bundle holds them for search.
- **Internal.** Nothing here may be shared outside the company; speakers' slides are their copyright.
- **Versions.** Adding a key is free; renaming or removing one makes `/2`. Readers check `schema` first.

## What Cortex may do with it (planned, phase 4)

Offer a session's `followups` as tasks on Nathan's word, never automatically; show a person's conference appearances on their
Cortex page by matching speaker names; let Ask Cortex cite a takeaway with its event, session and cite.
