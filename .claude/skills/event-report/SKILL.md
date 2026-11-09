---
name: event-report
description: Write a conference's themes (themes.yaml) and event report (report.md) in Conference Notes from its session summaries. Use when Nathan asks for the report, the themes or the write-up of a conference, or when the last session of an event has been summarised.
---

# Event report

Design: `docs/design.md` (§2 "Themes" and "Event report"). Leader text rules: short exact sentences, no method talk, sources at
the end, the speaker's hedges kept, whey never named.

## 1. Read everything

`data/events/<event-id>/`: `event.yaml`, every `sessions/*/session.yaml` and `summary.md`, and the originals where a summary
is thin. Note which sessions are `captured` only (no summary): the report says they are not yet summarised; it never
summarises them from memory.

## 2. `themes.yaml`

For each theme that ran through the event (two or more sessions, or one session Nathan rated high):

```yaml
themes:
- theme: <id from data/themes.yaml>
  headline: <one sentence: this event's version of the theme, with a count where there is one>
  strength: dominant | present | emerging
  evidence:
  - session: <session-id>
    quote: "<verbatim from a transcript, slide or notes>"
    where: "12:40"   # or "slide 7", "notes"
```

Every theme id must exist in `data/themes.yaml`; add to the vocabulary only when nothing fits (`first_seen: <event-id>`).
Two or three pieces of evidence per theme; every quote verbatim and from a session of this event.

## 3. `report.md`

Fixed headings, in this order:

```
# <event name>: event report
## In brief                five short lines a leader can read in a minute: what was said, flat, with counts
## Themes                  each theme in one paragraph: the headline, which sessions carried it, how it differs from last year's event if we have one
## Sessions that mattered  the sessions rated high, one line each with the takeaway and its cite
## People met              from the sessions' speakers and Nathan's notes: name, organisation, why they matter
## For Vita Actives        what changes for our range, pitches or customers; "my reading" where it is one
## Follow-ups              the sessions' follow-ups gathered, each with its session
## Sources                 the sessions read (ids), and which are not yet summarised
```

"In brief" is the text a leader reads: exact figures, no "may" turned into "will", no method talk.

## 4. Record, check, commit

Set `status: reported` in `event.yaml`. Run `python -m confnotes check`, `build`, `api`, `python -m pytest -q`,
`node dashboard/test/smoke.mjs`. Commit the event folder, `data/themes.yaml` if changed, `dashboard/data/events.json`,
`exports/api/v1/` with the usual trailer; push.

## 5. Reply

The "In brief" lines, then which sessions were left out for want of a summary. Ask for nothing else; follow-ups become Cortex
tasks only when Nathan says so.
