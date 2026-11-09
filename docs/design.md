# Conference Notes: design (v1, 9 Nov 2026)

What the tool is for, what it holds and the rules it follows. The build plan is `build_plan.md`; the API contract is `api.md`.

## 1. The idea

A record of what Nathan and the team learn at conferences such as the Sports & Active Nutrition Summit, Remedy, Vitafoods
and FiE: the presentations, the transcripts of talks, a summary and the takeaways of every session, the themes running
through an event, and one report per event. It answers three questions months later:

1. **What was said?** The original slides and transcript of a session, untouched, with the passages that matter quoted.
2. **What did we take from it?** A short summary, the takeaways, and what it means for Vita Actives, written once and reviewed.
3. **What is the industry talking about?** Themes, tracked across events and years, with the sessions that carried them.

It is its own tool in the Vita Actives suite, beside Cortex (meetings, projects, tasks), Market Intelligence
(`VA-Analysis`), ProductDB and the Black Book. Cortex reads it through the Suite API (`exports/api/v1/`); this tool reads
nothing from Cortex. A conference session is not a meeting: nobody owes anybody an action from it, so it does not belong in
Cortex's task machinery. What it produces is knowledge, so it is kept the way the Black Book keeps knowledge: plain text in
git, graded by how sure we are, every claim pointing at its source.

## 2. What it holds

```
data/
  themes.yaml                       the theme vocabulary (id, name, description): one id per theme, across events
  events/<event-id>/
    event.yaml                      name, dates, city, venue, organiser, who attended, links, status, to_check
    themes.yaml                     this event's themes: theme id, headline, the sessions and quotes that carry it
    report.md                       the event report (one per event, written after the sessions are summarised)
    sessions/<session-id>/
      session.yaml                  title, speakers, format, track, time, themes, ingredients, status, sources, to_check
      transcript.md                 the talk as transcribed, verbatim (never edited)
      notes.md                      Nathan's or a colleague's own notes, verbatim (never edited)
      summary.md                    the summary and takeaways (drafted by Claude, reviewed by a person)
      files/                        the presentation and handouts as received (PDF, PPTX, DOCX), plus <name>.txt
                                    with the text pulled out of each, slide by slide
```

Ids are lower-case words joined by hyphens: `sans-europe-2026`, `creatine-beyond-muscle`. An event id ends in its year.
Ids never change; a renamed session keeps its id.

### Originals and derived text

**Originals are never changed.** `transcript.md`, `notes.md` and everything in `files/` are kept as received. A transcript
from Otter, Circleback or a phone recording is converted to markdown (speaker, time, words) and then left alone.
The `<name>.txt` beside a presentation is pulled out by `python -m confnotes extract`, slide by slide, and is regenerated
rather than edited.

**Derived text cites its source.** Every takeaway and every theme headline points at the passages it rests on: a quote with
its time in the transcript (`[12:40]`), a slide number (`slide 7`) or a line in the notes. A takeaway without a passage is a
reading, and `summary.md` says so ("my reading").

### Session record (`session.yaml`)

| Field | Holds |
|---|---|
| `id`, `title` | the session as billed |
| `date`, `start`, `end` | when (`YYYY-MM-DD`, `HH:MM`) |
| `format` | `keynote`, `talk`, `panel`, `workshop`, `fireside`, `pitch`, `roundtable`, `exhibition`, `other` |
| `track` | the programme's track or room, as billed |
| `speakers` | list of `{name, organisation, role}` as billed |
| `themes` | theme ids from `data/themes.yaml` |
| `ingredients` | ingredients and products named, in our names where we have them (CreaWin, IsoClr: Pea, Oxystorm), else as said |
| `relevance` | `high`, `medium`, `low`: how much the session matters to Vita Actives (set at review) |
| `status` | `captured` (originals filed), `summarised` (summary drafted), `reviewed` (a person read and corrected it) |
| `summary_by`, `summary_date`, `reviewed_by`, `reviewed_date` | who wrote and who checked the summary, and when |
| `sources` | which originals exist: `transcript`, `notes`, `files` (each file: name, kind, pages, from whom) |
| `attended_by` | who was in the room |
| `links` | programme page, recording, speaker's published deck |
| `to_check` | what is still unknown or unconfirmed, one sentence |
| `added`, `added_by` | |

### Summary (`summary.md`)

Fixed headings, so the build can read each part:

```
# <session title>
## Summary            three to six sentences: what was argued, with the evidence the speaker gave
## Key takeaways      bullets; each ends with its source: [12:40], (slide 7), (notes)
## For Vita Actives   what it means for our range, customers or pitches; "my reading" where it is a reading
## Quotes             verbatim, with speaker and time or slide
## Follow-ups         people to contact, papers to find, questions left open (these become Cortex tasks only when Nathan says so)
```

### Themes

`data/themes.yaml` is the vocabulary: `id`, `name`, `description`, `first_seen` (event id). An event's `themes.yaml` lists
the themes that ran through it, each with a `headline` (one sentence, this event's version of the theme), `strength`
(`dominant`, `present`, `emerging`), and `evidence`: `{session, quote, where}`. A theme appears in the vocabulary once and in
as many events as carried it, so the dashboard can show a theme's history: where it started, how it changed.

### Event report (`report.md`)

Written after the sessions are summarised, with fixed headings: `## In brief` (five lines a leader can read), `## Themes`,
`## Sessions that mattered`, `## People met`, `## For Vita Actives`, `## Follow-ups`, `## Sources`. Leader text follows the
Market Intelligence rules: exact, short sentences, no method talk, sources at the end, hedges kept as the speaker gave
them ("may" never becomes "will").

## 3. How things get in

Everything comes through a Claude session, the way ProductDB fills its register:

- **`new-event`**: Nathan names an event ("I'm at SANS Europe today"); the skill creates `event.yaml` from what he said and the
  programme page, with gaps in `to_check`.
- **`add-session`**: Nathan drops a presentation, a transcript, a recording's export or his notes, with a line on which
  session it was. The skill files the originals, runs `extract`, drafts `summary.md` from the originals only, fills
  `session.yaml`, proposes themes (existing ids first, a new one only when nothing fits), runs the checks and commits.
  Nathan reads the draft; the status becomes `reviewed` only when he says so.
- **`event-report`**: once the sessions are summarised, the skill writes `themes.yaml` and `report.md` from the session
  summaries and quotes, runs the checks and commits. Nathan reviews.

Nothing is guessed. A field the sources do not give stays blank and is named in `to_check`. The AI does the understanding
(what a session argued, which theme it carried); code checks structure (ids resolve, headings present, dates valid).

## 4. What it gives

- **Dashboard** (`dashboard/`, static, plain JS, the suite's design): events, one page per event (sessions by day, themes,
  the report), one page per session (summary, takeaways, quotes, the slides' text slide by slide, the transcript), one page
  per theme (its history across events), speakers and organisations, ingredients named, a search over everything, and a
  "To check" list. Data comes only from `dashboard/data/events.json`, written by `python -m confnotes build` from the
  store, stamped with the commit, and refused while the store has problems.
- **Suite API v1** (`exports/api/v1/`): events, sessions, themes and takeaways as versioned JSON for Cortex and any agent
  (`docs/api.md`).
- **Leader text**: each report's "In brief".

## 5. Rules

1. Originals are never changed. Derived text cites passages.
2. Nothing is guessed; unknowns go in `to_check`.
3. Claude drafts, a person reviews; `reviewed` is set only by a person's word.
4. Health claims in a summary are the speaker's, reported with the speaker's hedge, never ours.
5. Ids never change. Theme ids are shared across events.
6. Generated files (`dashboard/data/`, `exports/api/v1/`, `files/*.txt`) are never hand-edited.
7. Internal: not for sharing. Speakers' slides are their copyright; they stay inside the company.
