"""extract.py: PPTX slides with notes, PDF pages, DOCX sections; markers the store counts; originals untouched."""
import hashlib

import docx

from confnotes import extract, store

SESS = "events/example-summit-2025/sessions/creatine-beyond-muscle"


def test_pptx_and_pdf(fixture_copy):
    folder = fixture_copy / SESS
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder / "files").iterdir()}
    done = extract.extract_session(folder)
    assert done == {"deck.pptx": 3, "handout.pdf": 2}
    deck = (folder / "files/deck.pptx.txt").read_text()
    assert deck.startswith("--- slide 1 ---\nCreatine beyond muscle")
    assert "--- slide 2 ---" in deck and "[notes]\nOpen with the history." in deck
    assert "n = 120 older women" in deck
    pdf = (folder / "files/handout.pdf.txt").read_text()
    assert "--- page 1 ---\nHandout page one" in pdf and "--- page 2 ---" in pdf
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (folder / "files").iterdir() if not p.name.endswith(".txt")}
    assert after == before  # originals never change
    s = store.load_session(folder)
    assert [(f["name"], f["pages"]) for f in s["files"]] == [("deck.pptx", 3), ("handout.pdf", 2)]


def test_docx_sections(tmp_path):
    d = docx.Document()
    d.add_heading("First", level=1)
    d.add_paragraph("One.")
    d.add_heading("Second", level=1)
    d.add_paragraph("Two.")
    t = d.add_table(rows=1, cols=2)
    t.rows[0].cells[0].text, t.rows[0].cells[1].text = "a", "b"
    p = tmp_path / "h.docx"
    d.save(p)
    text, n = extract.extract_text(p)
    assert n == 2
    assert "--- section 1 ---\nFirst\nOne." in text and "--- section 2 ---\nSecond\nTwo.\na | b" in text


def test_unknown_kind(tmp_path):
    p = tmp_path / "x.key"
    p.write_bytes(b"x")
    try:
        extract.extract_text(p)
    except ValueError as e:
        assert "cannot extract" in str(e)
    else:
        raise AssertionError("expected ValueError")


def test_no_files_folder(tmp_path):
    assert extract.extract_session(tmp_path) == {}
