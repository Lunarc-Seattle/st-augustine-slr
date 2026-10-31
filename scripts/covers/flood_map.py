"""'When does this spot go under?' map for the project page.

From outputs/covers/every_foot.gpkg (written by every_foot.py) each piece of city land gets
the first level, 0 to 9 ft, at which any NOAA layer floods it, and separately the first level
at which the ocean-connected (slr) layer does. Earlier than that means low-lying ground that
floods while still cut off from the sea.

Outputs in docs/figures/:
  floodmap.png       the map people see (2x), land coloured by first flood level
  floodmap-data.png  same extent at 1x, no antialiasing; red = first level + 10, green = first
                     sea level + 10, 1 = Census water, 30 = still dry at 9 ft, 0 = outside the city
  floodmap.json      extent, size, codes and the landmarks' positions

Run from the repo root after every_foot.py: PYTHONPATH=src .venv/bin/python scripts/covers/flood_map.py
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
from PIL import Image

matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
import pearls as pearl_lib

SRC = Path("outputs/covers/every_foot.gpkg")
OUT = Path("docs/figures")
M_PER_PX = 10.0  # data image resolution; the map is drawn at twice this density
PAD = 300.0
LEVELS = list(range(1, 10))
WATER, DRY, OFFSET = 1, 30, 10

# first-flood bands: deep teal floods first, pale aqua last; same family as the covers' flood colour
BAND = ["#0B4F5A", "#0F6E7A", "#138896", "#18A7B5", "#3FB9C4", "#66C8D1", "#8CD6DC", "#B0E3E7", "#D2EFF1"]
C = dict(sea="#8FB2B6", today="#E9B9A0", dry="#F5F1E8", outside="#FBFAF7", edge="#33393F")

city = gpd.read_file(SRC, layer="city").geometry.union_all()
land = gpd.read_file(SRC, layer="land").geometry.iloc[0]
fl = gpd.read_file(SRC, layer="flooded")
crs = fl.crs


def geom(kind, level):
    return fl[(fl["kind"] == kind) & (fl["level_ft"] == level)].geometry.iloc[0]


def first_bands(kinds):
    """{level: land that first floods at that level} for the union of the given kinds."""
    seen = None
    bands = {}
    for lv in [0, *LEVELS]:
        now = geom(kinds[0], lv)
        for k in kinds[1:]:
            now = now.union(geom(k, lv))
        bands[lv] = now if seen is None else now.difference(seen)
        seen = now if seen is None else seen.union(now)
    return bands, seen


any_bands, any_seen = first_bands(["slr", "low"])
sea_bands, _ = first_bands(["slr"])
water = city.difference(land)
dry = land.difference(any_seen)

x0, y0, x1, y1 = city.bounds
x0, y0, x1, y1 = x0 - PAD, y0 - PAD, x1 + PAD, y1 + PAD
W, H = round((x1 - x0) / M_PER_PX), round((y1 - y0) / M_PER_PX)


def canvas(scale, bg):
    fig = plt.figure(figsize=(W * scale / 100, H * scale / 100), dpi=100, facecolor=bg)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(x0, x0 + W * M_PER_PX)
    ax.set_ylim(y0, y0 + H * M_PER_PX)
    ax.set_axis_off()
    return fig, ax


def paint(ax, g, color, aa):
    if g is not None and not g.is_empty:
        gpd.GeoSeries([g], crs=crs).plot(ax=ax, color=color, linewidth=0, antialiased=aa)


def code_image(parts):
    """Rasterise [(geometry, code)] into one uint8 channel, exactly, without antialiasing."""
    fig, ax = canvas(1, "black")
    for g, code in parts:
        paint(ax, g, (code / 255, code / 255, code / 255), False)
    fig.canvas.draw()
    img = np.asarray(fig.canvas.buffer_rgba())[:, :, 0].copy()
    plt.close(fig)
    return img


red = code_image([(water, WATER), (dry, DRY)] + [(any_bands[lv], OFFSET + lv) for lv in [0, *LEVELS]])
green = code_image([(land, DRY)] + [(sea_bands[lv], OFFSET + lv) for lv in [0, *LEVELS]])
coded = (red >= OFFSET) & (red < DRY) & (green >= OFFSET)
green[coded] = np.maximum(green[coded], red[coded])  # edge pixels: the sea never arrives before the first flood
green[red == WATER] = WATER
green[red == 0] = 0
OUT.mkdir(parents=True, exist_ok=True)
Image.fromarray(np.dstack([red, green, np.zeros_like(red)]), "RGB").save(OUT / "floodmap-data.png", optimize=True)

# the map people see
fig, ax = canvas(2, C["outside"])
paint(ax, water, C["sea"], True)
paint(ax, dry, C["dry"], True)
paint(ax, any_bands[0], C["today"], True)
for lv in LEVELS:
    paint(ax, any_bands[lv], BAND[lv - 1], True)
gpd.GeoSeries([city], crs=crs).boundary.plot(ax=ax, color=C["edge"], linewidth=0.9, alpha=0.7)
fig.savefig(OUT / "floodmap.png", dpi=100, facecolor=C["outside"], metadata={"Software": None})
plt.close(fig)


def shrink(path, colors=128):
    """Flat colours only, so a 128-colour palette is visually lossless and about a quarter of the size."""
    im = Image.open(path).convert("RGB")
    im.quantize(colors=colors, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(path, optimize=True)


shrink(OUT / "floodmap.png")

P = pearl_lib.load(26917, "outputs/covers/sites_every_foot.csv")
info = {
    "crs": str(crs),
    "extent": [x0, y0, x0 + W * M_PER_PX, y0 + H * M_PER_PX],
    "width": W,
    "height": H,
    "m_per_px": M_PER_PX,
    "codes": {"outside": 0, "water": WATER, "dry": DRY, "level_offset": OFFSET},
    "colors": {"bands": BAND, **C},
    "landmarks": [
        {
            "name": r["label"],
            "fx": round((r["x"] - x0) / (W * M_PER_PX), 4),
            "fy": round((y0 + H * M_PER_PX - r["y"]) / (H * M_PER_PX), 4),
        }
        for _, r in P.iterrows()
    ],
    "source": "outputs/covers/every_foot.gpkg (NOAA SLR Viewer FL_NE, Census TIGER/Line 2025)",
}
(OUT / "floodmap.json").write_text(json.dumps(info, indent=1, ensure_ascii=False) + "\n")
print(W, "x", H, "px;", OUT / "floodmap.png")
