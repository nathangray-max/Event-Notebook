# Published team library

A separate private claude.ai artifact for Nathan's team: https://claude.ai/artifact/M1bnkiBYe2GE9K4kNYkVtZ. Nathan shares it from the
artifact's Share menu; it is a different link from the admin dashboard (dashboard/ARTIFACT.md).

What it holds: only summarised, non-confidential sessions (FiE's side conversations never appear), with each talk's
slides, key learnings, summary, what it means for Vita Actives, quotes and further detail. No leads, transcripts, Nathan's
notes, open questions or follow-ups. `python -m confnotes team` refuses to build if public text names a confidential
session or a confidential lead's company (tests/test_team.py).

Publish from a commit: `python -m confnotes team` (renders slide packs into team/build/slides, cached, git-ignored), commit,
copy `index.html` to a scratch folder and publish it with the files map from `python -m confnotes team-files`
(app.js, styles.css, data/library.json and slides/<event>--<session>.json). Leave out `test/` and this file.
After any change: `node team/test/smoke.mjs`.

Capabilities: none (the Ask the library assistant was removed on Nathan's word, 24 Nov 2026; version 5 cleared it).

| Version | Date | Commit | What changed |
|---|---|---|---|
| 1 | 2026-11-24 | 705266d | First version: Remedy CDMO (18 talks), SANS Europe (12), Healthspan Summit (14); 44 lessons, 619 slides; FiE's confidential conversations excluded. |
| 2 | 2026-11-24 | bd079ed | Field guide edition (Nathan's choice from five concepts): hub front page filtered by nine plain themes; talk page with the deck pinned beside the reading, deck progress, key learnings that open their slide, Now explore after the last slide. |
| 3 | 2026-11-24 | ba96df1 | Browsing by three kinds of tag (Nathan): market categories, ingredients (29 groups, top 10 in the menu), insight type; replaces the nine plain themes. |
| 4 | 2026-11-24 | 0f96bad | Ask the library: an assistant (sample capability) answering from the talks' notes, citing talks and slides. |
| 5 | 2026-11-24 | 68ac7da | Final build: the Ask the library assistant removed and its capability cleared (Nathan); data from a clean commit. |
| 6 | 2026-11-24 | 00f3c72 | A summary line on every talk in a list, sorting (newest or programme order, Essential first, A to Z), swipe between slides on phones. |
