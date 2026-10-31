"""Static cover, option b: plan at 5 ft (left) + duotone LOC photo B (right), 1200x700.

Run from the repo root after plan_frames.py: .venv/bin/python scripts/covers/plan_photo.py
"""

from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageFilter, ImageOps

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

W, H, LEVEL = 1200, 700, 5
OUT = Path("outputs/covers/st-augustine-plan.png")
if Path("/System/Library/Fonts/Avenir Next.ttc").exists():
    font_manager.fontManager.addfont("/System/Library/Fonts/Avenir Next.ttc")
    plt.rcParams["font.family"] = "Avenir Next"


def hexrgb(h):
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], float)


# left: map band of the @2x plan frame (top 90%), cropped around the old town and the coast
plan = Image.open(f"outputs/covers/plan/frame_{LEVEL}ft@2x.png").convert("RGB")
band = plan.crop((0, 0, plan.width, int(plan.height * 0.90)))
lw, lh = 770, 620
cw = int(band.height * lw / lh)
x0 = 330
left = band.crop((x0, 0, x0 + cw, band.height)).resize((lw, lh), Image.LANCZOS)

# right: duotone photo, portrait crop on the palms and the bay wall
photo = ImageOps.autocontrast(Image.open("data/frozen/loc/matanzas_bay_from_castillo_2020.jpg").convert("L"), cutoff=1)
rw, rh = W - lw - 30 - 30 - 20, lh
photo = ImageOps.fit(photo, (rw * 2, rh * 2), Image.LANCZOS, centering=(0.42, 0.6)).filter(ImageFilter.MedianFilter(3))
v = (np.asarray(photo, float) / 255) ** 0.85
# warm split-tone: deep teal shadows, muted sage mid-tones, warm cream highlights
stops = np.array([0.0, 0.5, 1.0])
cols = np.stack([hexrgb("#1F4E57"), hexrgb("#9DB3A8"), hexrgb("#F7EBDA")])
rgb = np.stack([np.interp(v, stops, cols[:, i]) for i in range(3)], -1)
right = Image.fromarray(rgb.astype(np.uint8))
right = right.resize((rw, rh), Image.LANCZOS)

fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
for img, x, w, text in (
    (left, 30, lw, f"Land newly flooded at +{LEVEL} ft of sea-level rise, St. Augustine (NOAA, Census, OSM)"),
    (right, 30 + lw + 20, rw, "Matanzas Bay from the Castillo (LOC, C. M. Highsmith)"),
):
    ax = fig.add_axes([x / W, (H - 25 - lh) / H, w / W, lh / H])
    ax.imshow(img)
    ax.set_axis_off()
    fig.text((x + w / 2) / W, 0.04, text, ha="center", va="center", fontsize=11 if w > 500 else 9.5, color="#4C5B5B")
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=100, facecolor="white", metadata={"Software": None})
print(OUT)
