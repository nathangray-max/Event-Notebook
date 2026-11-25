# Training library (pilot)

Nathan, 24-25 Nov 2026: onboarding and training modules on topics and ingredients, in a separate site with the same
functionality as the team library, cross-linked with it by shared tags. Pilot with five of the team's own training decks.
It lives in this repo for the pilot (`data/training/`, `training/`, `confnotes/training.py`); it can move to its own repo
if adopted.

## What it is

- A **course** is a topic area (e.g. "Ingredient foundations", "Markets"). A **module** is one training deck with its
  reading: the deck pinned left with progress, the reading on the right, key learnings that jump to their slide, a
  "Check your understanding" block, then "Further reading from the shows" (conference talks with the same tags).
- Audience: Vita Actives staff (onboarding, sales and commercial training). The material is ours, internal.
- The team library (conference talks) shows "Training on this topic" on talk and tag pages; the training site shows
  "Further reading from the shows". Links are computed at build time from shared tag ids (`data/facets.yaml`),
  never kept by hand. Confidential conference sessions are never linked (the team build's leak check applies).

## Store layout

```
data/training/
  <course-id>/course.yaml          id, name, short, description, order
  <course-id>/modules/<module-id>/
    module.yaml                    the record (below)
    summary.md                     the reading (below)
    files/                         the deck as received (pptx and/or pdf), plus a rendered .pdf if the original is pptx
```

`module.yaml` keys:

| key | value |
|---|---|
| id | the folder name (lowercase, hyphens) |
| title | the deck's own title |
| course | the course id |
| order | position in the course (1, 2, 3...) |
| owner | who the deck says made it (e.g. "Vita Actives Training & Development"); blank if not stated |
| version | the deck's own version or date if it states one (e.g. "V3", "H2 2026"); else blank |
| level | high (Essential), medium (Recommended), low (Background) |
| audience | who it is for, from the deck if stated (e.g. "commercial team"); else blank |
| minutes | reading-and-slides time estimate in minutes (our estimate: about 1 minute per slide) |
| categories | market category ids from data/facets.yaml (may be empty) |
| tags | insight-type ids from data/facets.yaml (at least one) |
| ingredients | the ingredients the deck covers, in plain words (they map to ingredient groups through facets.yaml) |
| deck | the file in files/ whose pages are the slides (a pdf) |
| source | the original file as received |
| status | draft, or reviewed (reviewed only on Nathan's word; reviewed_by then names him) |
| reviewed_by | blank until reviewed |
| to_check | gaps, doubts and claims to check, as one string |
| added, added_by | date and who |

`summary.md` sections, in this order:

- `## Summary`: prose, under 220 words, no cites. What the module teaches and why it matters to us.
- `## Key learnings`: at most six bullets, each cited `(slide N)` (N = PDF page of `deck`).
- `## In practice`: how a colleague uses this with customers: only what the deck says, cited; anything beyond the deck
  is marked "my reading".
- `## Check your understanding`: three to five questions, each a line `- Q: ...` followed by a line `  A: ... (slide N)`.
  Answers come from the deck.
- `## Key slides` (optional): up to four `(slide N)` lines with a few words each.
- `## Detail` (optional): anything else worth keeping.

## Rules

- **Nothing guessed.** Facts come from the deck. Gaps and doubts go in `to_check`.
- **Claims:** the deck is our own training material, but EU health claims still apply. Report a health statement with
  the deck's own wording and hedge; if a deck states a benefit as fact that looks wider than an authorised EU claim,
  keep the wording, and add it to `to_check` as "claim to check". Never strengthen a claim.
- **Figures** are stated as the deck gives them, with its source if it names one.
- **Whey** is never named in our own text (Summary, Key learnings, In practice); the deck's wording may keep it in Detail.
- No personal emails or phone numbers in our text.
- Generated files (`training/data/`, slide packs) are never hand-edited: regenerate.
