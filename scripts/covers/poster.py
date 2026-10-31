"""Poster cover (1200x700 @2x): what the project is, at a glance.

Left: kicker, title, one-line method, the five scenario bars (outputs/land_loss.csv)
and the landmarks with the level they first flood (outputs/sites_at_risk.csv).
Right: the 2.5D view at POSTER_LEVEL, rendered without its own headline.

Run from the repo root after persp.py: PYTHONPATH=src .venv/bin/python scripts/covers/poster.py
"""

import sys
import textwrap
from pathlib import Path

import matplotlib
import pandas as pd
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
import pearls as pearl_lib
import persp

POSTER_LEVEL = 5
OUT = Path("outputs/covers/st-augustine-poster.png")
W, H = 1200, 700
C = persp.C
ACCENT = pearl_lib.ACCENT

# right panel: the 2.5D scene, clean, at 2x
scene_path = Path("outputs/covers/persp/_poster_scene.png")
persp.W = int(0.62 * W)  # render the scene straight at the panel's aspect (no crop, no stretch)
fig = persp.render(POSTER_LEVEL, with_text=False)
fig.savefig(scene_path, dpi=200, facecolor="white")
plt.close(fig)
persp.W = W
scene = Image.open(scene_path).convert("RGB")

table = pd.read_csv("outputs/land_loss.csv")
total = table[table["kind"] == "total"].set_index("level_ft")["new_loss_pct_of_land"]
levels = [lv for lv in total.index if lv > 0]
P = pearl_lib.load(26917)

fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor="white")
ax = fig.add_axes([0.38, 0.0, 0.62, 1.0])
ax.imshow(scene, aspect="auto")
ax.set_axis_off()
# soften the join between text column and image
grad = fig.add_axes([0.38, 0.0, 0.06, 1.0])
grad.imshow([[(1, 1, 1, a) for a in [1 - i / 63 for i in range(64)]]], aspect="auto", extent=(0, 1, 0, 1))
grad.set_axis_off()
fig.text(
    0.985,
    0.03,
    f"2.5D view at +{POSTER_LEVEL} ft, heights and water x{persp.VZ:g}",
    ha="right",
    fontsize=8,
    color=C["text"],
    alpha=0.8,
)

x = 0.045
fig.text(x, 0.905, "SEA-LEVEL RISE  ·  ST. AUGUSTINE, FLORIDA", fontsize=10, color=ACCENT, fontweight="demibold")
fig.text(
    x,
    0.815,
    "When the sea\nrises 1 to 9 feet",
    fontsize=30,
    fontweight="bold",
    color=C["text"],
    va="top",
    linespacing=0.95,
)
fig.text(
    x,
    0.65,
    "A reproducible Python pipeline on NOAA, Census\nand OpenStreetMap data, checked on every run.",
    fontsize=11,
    color=C["text"],
    va="top",
    linespacing=1.35,
)

# bars: share of city land newly flooded
fig.text(x, 0.515, "City land newly under water", fontsize=10, color=C["text"], fontweight="demibold")
bars = fig.add_axes([x + 0.03, 0.315, 0.27, 0.18])
for i, lv in enumerate(levels):
    y = len(levels) - 1 - i
    v = total[lv]
    bars.barh(y, 100, color="#EEF3F3", height=0.62)
    bars.barh(y, v, color=C["flood"], height=0.62)
    bars.text(-2, y, f"+{lv} ft", ha="right", va="center", fontsize=9.5, color=C["text"])
    bars.text(v + 1.5, y, f"{v:.0f}%", ha="left", va="center", fontsize=9.5, color=C["text"], fontweight="demibold")
bars.set_xlim(0, 100)
bars.set_ylim(-0.6, len(levels) - 0.4)
bars.set_axis_off()

# landmarks, grouped by the level at which they first flood
fig.text(x, 0.255, "Landmarks reached by the water", fontsize=10, color=C["text"], fontweight="demibold")
y = 0.215
for lv in sorted({v for v in P["floods_at"] if v is not None}):
    names = [lab for lab, f in zip(P["label"], P["floods_at"], strict=False) if f == lv]
    fig.text(x, y, f"+{lv} ft", fontsize=9.5, color=ACCENT, fontweight="bold", va="top")
    text = textwrap.fill(",  ".join(names), 52)
    fig.text(
        x + 0.045,
        y,
        text,
        fontsize=9.5,
        color=C["text"],
        va="top",
        family="Baskerville",
        style="italic",
        linespacing=1.3,
    )
    y -= 0.03 + 0.03 * text.count("\n") + 0.02
fig.text(x, 0.03, "NOAA SLR Viewer  ·  Census TIGER/Line  ·  OpenStreetMap", fontsize=8, color=C["text"], alpha=0.8)
OUT.parent.mkdir(parents=True, exist_ok=True)
fig.savefig(OUT, dpi=200, facecolor="white", metadata={"Software": None})
scene_path.unlink()
print(OUT)
