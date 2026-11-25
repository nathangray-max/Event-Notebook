# Published training library

A separate private claude.ai artifact for Vita Actives staff (docs/training.md): not yet published. After the first publish,
put its url in `data/sites.yaml` (`training:`) and rebuild both libraries, so the two sites link to each other. Nathan
shares it from the artifact's Share menu; it is a different link from the team library (team/ARTIFACT.md).

What it holds: the training modules in data/training, each with its deck, summary, key learnings, In practice, the
Check your understanding quiz and "Further reading from the shows" (team library talks on the same tags). No to_check,
added_by or reviewer fields. `python -m confnotes training` refuses to build while `python -m confnotes check` reports
training problems.

Links between the libraries are computed at build time from shared tags and the urls in `data/sites.yaml`; a blank url
shows the link as plain text naming the other library. Each build reads the other's output, so build in this order:

1. `python -m confnotes team` (the talks the modules link to);
2. `python -m confnotes training` (renders slide packs into training/build/slides, cached, git-ignored; writes
   training/data/library.json);
3. `python -m confnotes team` again (adds "Training on this topic" to talks and tag pages), then republish the team
   library too (team/ARTIFACT.md) if its links changed.

Publish from a commit: run the steps above, `python -m pytest -q`, `node training/test/smoke.mjs` and
`node team/test/smoke.mjs`, commit, copy `index.html` to a scratch folder and publish it with the files map from
`python -m confnotes training-files` (app.js, styles.css, data/library.json and slides/<course>--<module>.json).
Leave out `test/` and this file.

Capabilities: none.

| Version | Date | Commit | What changed |
|---|---|---|---|
| 1 | 2026-11-25 | 4897f7f | Pilot: two courses, five modules (vitamins, amino acids, fibres and prebiotics, mushrooms, GLP-1 market intelligence), all draft; links to the team library as plain text. |
| 2 | 2026-11-25 | 4097550 | Links to the team library live (data/sites.yaml). |
