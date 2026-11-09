"""Photos of slides: file them small, and hold their text (docs/design.md §2, "Photos").

A photo of a slide is filed as a reduced copy (WebP, longest side 1600 px): the full-size original stays on the phone.
Its text is not pulled out by code (no OCR here): Claude reads the photo in the session and writes `<name>.txt` beside it,
one `--- photo N ---` block per photo, marked as a transcription.  `python -m confnotes photos <event> <session>` does the
reduction for every JPEG, PNG or WebP in files/ (HEIC needs converting on the phone first).
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_SIDE = 1600


def reduce_photos(folder: Path) -> Dict[str, str]:
    """Replace every image in <session>/files with a reduced WebP copy.  Returns {old name: new name}."""
    from PIL import Image, ImageOps
    files = folder / "files"
    done: Dict[str, str] = {}
    if not files.is_dir():
        return done
    for p in sorted(files.iterdir()):
        if p.suffix.lower() not in IMAGE_EXTS or not p.is_file():
            continue
        img = ImageOps.exif_transpose(Image.open(p))
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE))
        out = p.with_suffix(".webp")
        if out == p and p.stat().st_size < 400_000:
            continue  # already small
        img.convert("RGB").save(out, "WEBP", quality=82, method=6)
        if out != p:
            p.unlink()
            txt = files / (p.name + ".txt")
            if txt.exists():
                txt.rename(files / (out.name + ".txt"))
        done[p.name] = out.name
    return done
