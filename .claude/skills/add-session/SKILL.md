---
name: add-session
description: File a conference session in Conference Notes from what Nathan sends (a presentation, a transcript, a recording's export, his notes, or a line about the talk) and draft its summary and takeaways. Use whenever Nathan uploads or pastes material from a conference talk, panel or workshop.
---

# Add a session

Design: `docs/design.md` (§2 for the record, §3 for how things get in). Loader and checks: `confnotes/store.py`.

Input: one or more originals (PDF or PPTX slides, a DOCX handout, a transcript, Nathan's notes) and a line on which session it
was and at which event. Several uploads for one talk are one session; one upload covering several talks is several sessions.

## 1. Place the session

- Find the event: `ls data/events/`. If it does not exist, run the `new-event` skill first.
- Search the event's sessions for the same talk (title, speaker). If it exists, add to it; never a duplicate.
- Create it: `python -m confnotes new-session <event-id> <session-id> --title "<title as billed>" --date YYYY-MM-DD --start HH:MM --end HH:MM --format <keynote|talk|panel|workshop|fireside|pitch|roundtable|exhibition|other> --track "<room or track>"`.
  The id is the title in lower-case words joined by hyphens, shortened (`creatine-beyond-muscle`).

## 2. File the originals (never changed)

- Presentations and handouts: copy as received into `files/` (keep the file name readable; a `.pptx` stays a `.pptx`).
  Over 25 MB: keep a link in `links` instead and say so in `to_check`.
- Transcript: `transcript.md`, verbatim. A recording export (Otter, Circleback, a `.vtt` or `.srt`) is converted to lines of
  `[mm:ss] Speaker: words` and then left alone. Do not correct, trim or tidy what was said.
- Nathan's notes: `notes.md`, verbatim, as he wrote them.
- Run `python -m confnotes extract <event-id> <session-id>`: it writes `files/<name>.txt`, slide by slide (`--- slide 3 ---`),
  with speaker notes under `[notes]`. Read those `.txt` files; never the binary.

## 3. Fill `session.yaml`

From the originals and the programme only: `speakers` (name, organisation, role as billed), `track`, times, `ingredients`
named (our names where we have them: CreaWin, `"IsoClr: Pea"` (quoted: a colon in a YAML list needs quotes), Oxystorm; otherwise as said), `attended_by`, `links`.
`relevance` and `status` are set below. Unknowns go in `to_check`, one sentence.

## 4. Draft `summary.md`

Only from the originals in the folder. Fixed headings, in this order, each present even when short:

```
# <title>
## Summary          three to six sentences: what was argued and the evidence the speaker gave
## Key takeaways    bullets; each ends with its passage: [12:40] (transcript time), (slide 7), (page 3), (notes)
## For Vita Actives what it means for our range, customers or pitches; write "my reading" where it is one
## Quotes           verbatim, with speaker and time or slide
## Follow-ups       people to contact, papers to find, open questions
```

Rules:
- Every takeaway cites a passage. A takeaway without one is a reading and says "my reading". The build marks uncited takeaways.
- Health claims and figures are the speaker's, with the speaker's hedge kept ("may" never becomes "will"; "in one trial" stays).
  Never add a claim the speaker did not make, and never upgrade one.
- Quotes are word for word from the transcript or slide. If there is no transcript, quote the slide, not your memory.
- Whey is never named in text a leader reads (Market Intelligence decision); describe the format or category instead.
- Short sentences, British English, no method talk.

Set in `session.yaml`: `status: summarised`, `summary_by: Claude`, `summary_date: <today>`, `relevance` (high, medium, low:
how much it matters to Vita Actives, with one reason in the "For Vita Actives" section).

## 5. Themes

Read `data/themes.yaml`. Put the ids of the themes the session carried in `session.yaml` `themes`. Add a theme to the
vocabulary only when none fits: `id`, `name`, `description` (one sentence), `first_seen: <event-id>`. Prefer one broader
theme over two narrow ones; the event's own version of a theme goes in the event's `themes.yaml` later (`event-report`).

## 6. Check, build, commit

`python -m confnotes check` (must print no problems), `python -m confnotes build`, `python -m confnotes api`,
`python -m pytest -q`. Commit the session folder, `data/themes.yaml` if changed, `dashboard/data/events.json` and
`exports/api/v1/` with the usual trailer, and push.

## 7. Reply

Three lines: the session filed (event, title, what originals), the three strongest takeaways with their cites, what is still to
check. Then: "Say 'reviewed' when you have read it and I will mark it so." Set `status: reviewed`, `reviewed_by: Nathan`,
`reviewed_date` only on his word, after applying any corrections he gives.
