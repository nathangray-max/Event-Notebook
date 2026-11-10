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
- Create it: `python -m confnotes new-session <event-id> <session-id> --title "<title as billed>" --date YYYY-MM-DD --start HH:MM --end HH:MM --format <keynote|talk|panel|workshop|fireside|breakout|pitch|roundtable|exhibition|other> --track "<room or track>"`.
  The id is the title in lower-case words joined by hyphens, shortened (`creatine-beyond-muscle`).

## 2. File the originals (never changed)

- Presentations and handouts: copy as received into `files/` (keep the file name readable; a `.pptx` stays a `.pptx`).
  Over 25 MB: keep a link in `links` instead and say so in `to_check`.
- Photos of slides: copy into `files/`, run `python -m confnotes photos <event-id> <session-id>` (reduced WebP copies), then
  read each photo and write `files/<name>.txt`: a first line "Transcribed by Claude from the photo; the photo is the original.",
  then one `--- photo N ---` block per photo with the slide's text as written. Cite as `(photo 2)`.
- Otter recordings: find the recording with the Otter tools (`otter_search` by date, `otter_fetch` by id). Write
  `transcript.md` as: `# <title>: transcript`, a line `Source: Otter.ai recording "<title>", <url>, recorded <date> <local time>,
  <length>. Speaker labels are Otter's.`, a blank line, then one line per speaker turn `[mm:ss] Speaker: words`, verbatim.
  Save Otter's automatic summary as `files/otter-summary.md`, headed "Otter.ai's automatic summary, as received. Not ours."
  Put the recording's link in `links.otter`.
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

Only from the originals in the folder. A summary must read as a summary (Nathan, 10 Nov 2026). Model:
`data/events/sans-europe-2026/sessions/unfiltered-an-insider-s-view-of/summary.md`. Headings in this order (Key slides
and Detail are optional):

```
# <title>
## Summary          2-4 short paragraphs of prose, under 220 words: who spoke, the question, the argument in their
                    order, the conclusion. Two or three figures at most. No cites, no "my reading".
## Key takeaways    3-6 bullets, the most important findings; each ends with its passage: [12:40], (photo 7), (slide 7), (notes)
## Key slides       only when files/ holds slide photos: up to 4, "- (photo N) one-line caption", the slides that carry the argument
## For Vita Actives 2-5 bullets: what it means for our range, customers or pitches; "my reading" where it is one
## Quotes           2-4, verbatim; each an exact substring of the transcript or a slide's text ("..." where it starts mid-sentence)
## Detail           every other figure and point worth keeping, cited bullets
## Follow-ups       people to contact, papers to find, open questions
```

Rules:
- Every takeaway and Detail bullet cites a passage. One without a passage is a reading and says "my reading".
- Health claims and figures are the speaker's, with the speaker's hedge kept ("may" never becomes "will"; "in one trial" stays).
  Never add a claim the speaker did not make, and never upgrade one.
- Check every quote is an exact substring of its source with a script before finishing.
- When slide photos arrive after the summary was written, revise it: exact slide figures replace approximate spoken ones
  (cite both), new points go to Detail, the best slides become Key slides.
- Whey is never named in text a leader reads (Market Intelligence decision); describe the format or category instead.
- Whey market (prices, supply, capacity, timing): record what the speaker said in Key takeaways or Detail, but base
  "For Vita Actives" readings only on Alan Johnstone's account at SANS Europe 2026 (`sans-europe-2026/unfiltered-an-insider-s-view-of`),
  Nathan's reference (decision 10 Nov 2026). A conflicting figure from another speaker is noted, never adopted.
- Short sentences, British English, no method talk.

Set in `session.yaml`: `status: summarised`, `summary_by: Claude`, `summary_date: <today>`, `relevance` (high, medium, low:
how much it matters to Vita Actives, with one reason in the "For Vita Actives" section).

 leader reads (Market Intelligence decision); describe the format or category instead.
