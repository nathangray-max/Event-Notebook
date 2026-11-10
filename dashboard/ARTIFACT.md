# Published dashboard

Private claude.ai artifact: https://claude.ai/artifact/UpL7V3Ly6oexgCAZBnDGUk

Publish from a commit, never the working tree: `git archive <commit> dashboard` into a scratch folder,
publish `index.html` to the URL above with `app.js`, `styles.css` (text/css) and `data/events.json` in the files map.
Leave out `test/` and this file. Slide photos are not published: the dashboard shows each slide's transcribed text.

| Version | Date | Commit | What changed |
|---|---|---|---|
| 1 | 2026-11-10 | af08850 (data from 43bf5fe) | First version: SANS Europe 2026 (15 sessions, 5 summarised, 74 slide photos as text) and Remedy CDMO 2026 (15 sessions, all summarised); 19 themes; search over summaries, slide text and transcripts. |
| 2 | 2026-11-10 | cd25bc3 (data from 6cb8e9c) | First version from `nathangray-max/Event-Notebook`. SANS Europe afternoon: Marchon fireside, GLP-Won, From hype to proof and the GLP-1 panel summarised; SANS marked attended. Nutra Healthspan Summit 2026 added, with Euromonitor's opening talk. 31 sessions, 25 summarised. |
