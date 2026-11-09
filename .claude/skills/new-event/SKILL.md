---
name: new-event
description: Create the record of a conference in Conference Notes (data/events/<event-id>/event.yaml). Use when Nathan names a conference he is at, is going to, or has been to (SANS Europe, Remedy, Vitafoods, FiE) and no event folder exists for it yet.
---

# New event

Design: `docs/design.md`. The store's loader and checks: `confnotes/store.py`.

1. **Check it is new.** `ls data/events/` and read the names; an event id ends in its year (`sans-europe-2026`). If the event
   exists, edit its `event.yaml` instead (never a second folder).
2. **Read the programme.** Fetch the event page with WebFetch (dates, venue, organiser, programme). If the host is blocked by the
   session's network settings, say so and record what Nathan said, with the gaps in `to_check`.
3. **Create it:**
   ```sh
   python -m confnotes new-event <event-id> --name "<name as the organiser writes it>" --short "<short name>" \
     --start YYYY-MM-DD --end YYYY-MM-DD --city ... --country ... --venue ... --organiser ... --url ... --status attending
   ```
   `status`: `planned` before, `attending` during, `attended` after, `reported` once `report.md` exists (set by `event-report`).
   Then fill `attended_by`, `links` (programme, recordings) and `description` in the yaml. Nothing is guessed: a field the
   page and Nathan do not give stays blank and is named in `to_check`.
4. **Check and build:** `python -m confnotes check`, then `python -m confnotes build` and `python -m confnotes api`.
5. **Commit and push** `data/events/<event-id>/`, `dashboard/data/events.json` and `exports/api/v1/` with the usual trailer.
6. **Reply in two lines:** what was created and what is still to check. Offer nothing else; the sessions come as Nathan sends them.
