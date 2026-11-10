import shutil
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixture"


@pytest.fixture
def fixture_copy(tmp_path):
    """A writable copy of the synthetic store (tests/fixture), without its extracted .txt files."""
    dst = tmp_path / "data"
    shutil.copytree(FIXTURE, dst)
    for p in dst.rglob("files/*.txt"):
        if not p.name.endswith(".webp.txt"):  # a photo's text is transcribed, not extracted: it stays
            p.unlink()
    return dst
