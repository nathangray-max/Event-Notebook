# Published dashboard

Private claude.ai artifact: https://claude.ai/artifact/UpL7V3Ly6oexgCAZBnDGUk

Publish from a commit, never the working tree: `git archive <commit> dashboard` into a scratch folder,
publish `index.html` to the URL above with `app.js`, `styles.css` (text/css) and `data/events.json` in the files map, plus
every slide photo: `python -m confnotes publish-files` prints their map (`slides/<event>/<session>/<file>` to its source).
Leave out `test/` and this file.

| Version | Date | Commit | What changed |
|---|---|---|---|
| 1 | 2026-11-10 | af08850 (data from 43bf5fe) | First version: SANS Europe 2026 (15 sessions, 5 summarised, 74 slide photos as text) and Remedy CDMO 2026 (15 sessions, all summarised); 19 themes; search over summaries, slide text and transcripts. |
| 2 | 2026-11-10 | cd25bc3 (data from 6cb8e9c) | First version from `nathangray-max/Event-Notebook`. SANS Europe afternoon: Marchon fireside, GLP-Won, From hype to proof and the GLP-1 panel summarised; SANS marked attended. Nutra Healthspan Summit 2026 added, with Euromonitor's opening talk. 31 sessions, 25 summarised. |
| 3 | 2026-11-10 | 4ab2f9b (data from e7053f4) | Summaries that read as summaries (Nathan): a prose summary, up to six takeaways, key slides as photos, the rest under Detail. 86 slide photos published under `slides/`; photo cites open the slide. Nick Stene's slides and IM8, Ancient + Brave settled. |
| 4 | 2026-11-10 | 2a30fe8 | Data only: Ewa Hudson (Lumina Intelligence) summarised. |
| 5 | 2026-11-10 | 6850ec3 | Data only, plus the panel's two photos: all speakers' perspectives restored (Nathan's clarification); the 'From hype to healthspan' panel added, transcript to come. |
| 6 | 2026-11-10 | cf6f1f6 | Data only: the 'From hype to healthspan' panel and Jens Walter's microbiome talk summarised. |
| 7 | 2026-11-10 | 7290664 | Healthspan day 1 complete from the agenda: billed titles, the afternoon's four sessions with ALT's slides, unrecorded sessions as placeholders. |
| 8 | 2026-11-10 | c49e6db | Data only: the consumer insights panel summarised. |
