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
| 9 | 2026-11-17 | 769bd88 | Data only: FiE 2026 created; three confidential side conversations (Clasado, AIDP, Fairfield Nutech), AIDP summarised with desk research. |
| 10 | 2026-11-17 | 59bcded | Data only: Clasado summarised with desk research (confidential). |
| 11 | 2026-11-17 | 8a16b25 | Data only: Fairfield Nutech (most likely Fayrefield Nutratek) summarised with desk research (confidential). |
| 12 | 2026-11-23 | c855a0d | Data only: Remedy's Aker BioMarine krill deck (new session) and Nick Morgan's slides (summary revised with slide figures). |
| 13 | 2026-11-23 | 761c3aa | Data only: Remedy decks for Nuritas, MartinBauer, SPI Pharma, Kaneka, Tantus, Solabia, H&B, HMT, Sacco, The Protein Brewery and Aquanova revise their summaries; Favea and Nathan's own talk added. |
| 14 | 2026-11-23 | 662b6e2 | Data only: SANS decks for Alan Johnstone, Rousselot, Lumina and Zariwala revise their summaries; Mark Evans and Sharon Madigan summarised; Emily Jevons added. |
| 15 | 2026-11-23 | 55eafba | Data only: SANS photo-based summaries final (no further slides exist); Cellaro confirmed in Nick Morgan's SANS keynote. |
| 16 | 2026-11-23 | ab32aa7 | Data only: Healthspan decks (Weinkove, Hudson, Walter, Gut, Selman/Yu, Macciochi, Tongiani) filed and summarised; SANS and Healthspan marked complete for slides. Handover: docs/handover-2026-11-23.md. |
| 17 | 2026-11-24 | 68ac7da | Data only, final build: tags (ingredient groups, market categories, insight types) in the data; clean stamp. |
| 18 | 2026-11-24 | 558a42b | Data only: Matts Johansen (CEO, Aker BioMarine) on the closing panel and the krill talk; Martina Pavlová confirmed. |
| 19 | 2026-11-24 | 49152e7 | Data only: archive events Probiota 2025 (23 sessions, 18 with Otter transcripts) and Active Nutrition Summit 2025 (26 sessions, matched to the advance programme); Marit Veenstra's name corrected at Remedy; neutral pronouns in the archive events. |
