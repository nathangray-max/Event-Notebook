"""Pull the text out of the originals in a session's files/ folder (docs/design.md §2, "Originals and derived text").

For every PDF, PPTX or DOCX in files/ it writes `<name>.txt` beside it: the text, with a marker before each page or slide
(`--- slide 3 ---`), so a takeaway can cite "slide 3".  Speaker notes in a PPTX follow their slide under `[notes]`.
The original is never touched.  Existing .txt files are rewritten (they are generated, never edited).

    python -m confnotes extract <event-id> [<session-id>]      every session of the event, or one
    python -m confnotes extract --all
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

EXTRACTABLE = {".pdf", ".pptx", ".docx"}


def _clean(text: str) -> str:
    text = text.replace("\r", "")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def pdf_pages(path: Path) -> List[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return [_clean(p.extract_text() or "") for p in reader.pages]


def pptx_slides(path: Path) -> List[str]:
    from pptx import Presentation
    prs = Presentation(str(path))
    out = []
    for slide in prs.slides:
        parts: List[str] = []
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = "\n".join(p.text for p in shape.text_frame.paragraphs if p.text.strip())
                if t.strip():
                    parts.append(t)
            if getattr(shape, "has_table", False) and shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        parts.append(" | ".join(cells))
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame is not None:
            n = slide.notes_slide.notes_text_frame.text.strip()
            if n:
                parts.append("[notes]\n" + n)
        out.append(_clean("\n".join(parts)))
    return out


def docx_sections(path: Path) -> List[str]:
    """A Word document as one section per top-level heading (or one section when it has none)."""
    import docx
    d = docx.Document(str(path))
    sections: List[List[str]] = [[]]
    for p in d.paragraphs:
        if p.style is not None and p.style.name.lower().startswith("heading 1") and sections[-1]:
            sections.append([])
        if p.text.strip():
            sections[-1].append(p.text)
    for t in d.tables:
        for row in t.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                sections[-1].append(" | ".join(cells))
    return [_clean("\n".join(s)) for s in sections if s] or [""]


def extract_text(path: Path) -> Tuple[str, int]:
    """The text of one file with page markers, and the page count."""
    ext = path.suffix.lower()
    if ext == ".pdf":
        pages, word = pdf_pages(path), "page"
    elif ext == ".pptx":
        pages, word = pptx_slides(path), "slide"
    elif ext == ".docx":
        pages, word = docx_sections(path), "section"
    else:
        raise ValueError(f"cannot extract text from {path.name}")
    body = "\n\n".join(f"--- {word} {i} ---\n{t}" for i, t in enumerate(pages, start=1))
    return body + "\n", len(pages)


def extract_session(folder: Path) -> Dict[str, int]:
    """Write <name>.txt for every extractable file in <session>/files.  Returns {file name: pages}."""
    files = folder / "files"
    done: Dict[str, int] = {}
    if not files.is_dir():
        return done
    for p in sorted(files.iterdir()):
        if p.suffix.lower() in EXTRACTABLE and p.is_file():
            text, n = extract_text(p)
            (files / (p.name + ".txt")).write_text(text, encoding="utf-8")
            done[p.name] = n
    return done
