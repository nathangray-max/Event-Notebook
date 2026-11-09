"""photos.py: images reduced to WebP at 1600 px, text sidecars renamed, photo kinds in the store, (photo N) and (otter) cites."""
from PIL import Image

from confnotes import build, photos, store


def test_reduce_and_sidecar(tmp_path):
    files = tmp_path / "files"; files.mkdir()
    Image.new("RGB", (4000, 3000), "white").save(files / "IMG_0001.jpg", quality=90)
    Image.new("RGB", (800, 600), "white").save(files / "small.png")
    (files / "IMG_0001.jpg.txt").write_text("Transcribed by Claude from the photo; the photo is the original.\n--- photo 1 ---\nSlide text\n")
    done = photos.reduce_photos(tmp_path)
    assert done == {"IMG_0001.jpg": "IMG_0001.webp", "small.png": "small.webp"}
    assert not (files / "IMG_0001.jpg").exists() and (files / "IMG_0001.webp.txt").exists()
    w, h = Image.open(files / "IMG_0001.webp").size
    assert max(w, h) == 1600
    recs = store._files(files)
    assert [(r["name"], r["kind"], r["pages"]) for r in recs] == [("IMG_0001.webp", "photo", 1), ("small.webp", "photo", None)]
    assert recs[0]["text"].startswith("Transcribed by Claude")


def test_photo_and_otter_cites():
    assert build.cites("the dose was 3 g (photo 2), said twice (otter) and at [04:10]") == ["photo 2", "otter", "04:10"]


def test_no_images(tmp_path):
    (tmp_path / "files").mkdir()
    assert photos.reduce_photos(tmp_path) == {}
