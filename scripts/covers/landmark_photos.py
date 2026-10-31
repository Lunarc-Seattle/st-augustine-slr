"""640 px web copies of the frozen Library of Congress landmark photos (data/frozen/loc/SOURCES.md).

Run from the repo root: .venv/bin/python scripts/covers/landmark_photos.py
"""

from pathlib import Path

from PIL import Image

SRC = Path("data/frozen/loc")
OUT = Path("docs/figures/landmarks")
PHOTOS = {
    "castillo_de_san_marcos_2020.jpg": "castillo.jpg",
    "constitution_monument_plaza_2020.jpg": "plaza.jpg",
    "fountain_of_youth_entrance_2020.jpg": "ponce.jpg",
}

OUT.mkdir(parents=True, exist_ok=True)
for src, dst in PHOTOS.items():
    im = Image.open(SRC / src).convert("RGB")
    im.thumbnail((640, 640))
    im.save(OUT / dst, quality=84, optimize=True, progressive=True)
    print(OUT / dst)
