"""Plan-style animation frames (estuary-plan look): St. Augustine as the sea rises 0 to 9 ft.

Vector rendering at 1200x700 (and @2x), from data/cache/covers/layers_wide.gpkg (NOAA, Census, OSM),
data/frozen/osm_buildings.geojson (OSM, frozen) and outputs/land_loss.csv for the captions.
Water depth bands are distance-from-shore rings of the Census water, not bathymetry.

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/plan.py
"""

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import pandas as pd
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
import pearls as pearl_lib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

L = Path("data/cache/covers/layers_wide.gpkg")
OUT = Path("outputs/covers/plan")
LEVELS = [0, 1, 3, 5, 7, 9]
W, H = 1200, 700
CAPTION = 0.10  # share of the height under the map

C = dict(
    contour="#8E6A4B",
    contour_light="#B08D6E",
    water="#2F83BE",
    water_mid="#7DB6DC",
    water_fill="#BFDDF0",
    veg="#86AE7C",
    veg_fill="#D3E6C6",
    soil="#E9DFCF",
    paper="#F6F1E7",
    marsh="#E8C9B0",
    ink="#8E6A4B",  # no black: text, scale bar and arrow in the banner brown
    bldg="#C8B49C",
    muted="#4C5B5B",
    flood="#18A7B5",  # saturated aqua: new flooding, distinct from the muted sea (same as the 2.5D)
    flooded_bldg="#0F7E8C",
)
SERIF, SANS = "Baskerville", "Avenir Next"
for f in ("/System/Library/Fonts/Supplemental/Baskerville.ttc", "/System/Library/Fonts/Avenir Next.ttc"):
    if Path(f).exists():
        font_manager.fontManager.addfont(f)
plt.rcParams["font.family"] = SANS
plt.rcParams["hatch.linewidth"] = 0.5


def layer(name):
    return gpd.read_file(L, layer=name)


frame, land, water, marsh, city = (layer(n) for n in ("frame", "land", "water", "marsh", "city"))
parks, historic = layer("parks"), layer("historic")
new = {lv: layer(f"new_{lv}") for lv in LEVELS if lv > 0}
bldg = gpd.read_file("data/frozen/osm_buildings.geojson").to_crs(frame.crs)
bldg = bldg[bldg.intersects(city.geometry.iloc[0])].reset_index(drop=True)  # study area only
x0, y0, x1, y1 = frame.total_bounds
x0 += 800  # shift the view east: less empty mainland, coast nearer the middle
crs = frame.crs

# distance-from-shore rings: paler near the shore, deeper offshore
land_s = land.geometry.iloc[0].simplify(4)
water_g = water.geometry.iloc[0]
city_g = city.geometry.iloc[0]
pieces = gpd.GeoSeries([water_g], crs=crs).explode(index_parts=False)
keep = pieces[(pieces.area > 2e5) | pieces.intersects(city_g)]
water_g = keep.union_all()
water = gpd.GeoDataFrame(geometry=[water_g], crs=crs)
RINGS = [60, 160, 320, 600, 1000]
ring_colors = ["#E7EFEF", "#DCE8E8", "#CFE0E1", "#C1D7D9", "#B2CDD0", "#A4C3C7"]  # muted sea, as in the references
bands, inner = [], None
for d in [*RINGS, None]:
    zone = water_g if d is None else water_g.intersection(land_s.buffer(d))
    band = zone if inner is None else zone.difference(inner)
    bands.append(band)
    inner = zone
shore_lines = gpd.GeoSeries([land_s.buffer(d).boundary for d in (14, 32, 55, 85, 125, 180, 250, 340)], crs=crs)
shore_lines = shore_lines.intersection(water_g)

# flooded buildings per level (touching land newly flooded at that level)
hit = {}
for lv, g in new.items():
    idx = bldg.sindex.query(g.geometry.iloc[0], predicate="intersects")
    hit[lv] = set(idx)

PEARLS = pearl_lib.load(crs)
HL_FILL, HL_LINE = pearl_lib.highlight_areas(PEARLS)
HL_FILL_G = gpd.GeoSeries(HL_FILL, crs=crs).union_all()
HL_BLDG = bldg.intersects(HL_FILL_G).values  # landmark buildings, coloured in the accent
PEARL_OFFSETS = {  # label offsets in points; layout only
    "1513 Ponce Landing Memorial": (-18, 6),
    "Castillo de San Marcos": (-18, 10),
    "Plaza de la Constitución": (-18, 0),
    "Lincolnville Historic District": (-18, -4),
    "Oglethorpe Battery Park": (18, 14),
    "Lighthouse Park": (18, 16),
    "Anastasia State Park": (-18, -18),
}
table = pd.read_csv("outputs/land_loss.csv")
pct = table[table["kind"] == "total"].set_index("level_ft")["new_loss_pct_of_land"]

WATER_LABELS = {  # Census FULLNAME -> (x, y, rotation); positions are layout only
    "Atlantic Ocean": (474300, 3308400, 0),
    "Matanzas Riv": (471150, 3305200, 68),
    "San Sebastian Riv": (468600, 3306250, 84),
}
WORDS = {"Riv": "River", "Inlt": "Inlet"}
SITE_LABELS = {  # OSM name -> label offset in metres
}


def draw_map(ax, level):
    ax.set_facecolor(C["paper"])
    for band, col in zip(bands, ring_colors, strict=False):
        gpd.GeoSeries([band], crs=crs).plot(ax=ax, color=col, linewidth=0, zorder=1)
    for i, line in enumerate(shore_lines):
        gpd.GeoSeries([line], crs=crs).plot(ax=ax, color="#6E969C", linewidth=0.35, alpha=0.55 - i * 0.05, zorder=2)
    land.plot(ax=ax, color=C["paper"], linewidth=0, zorder=3)
    water.boundary.plot(ax=ax, color="#6E969C", linewidth=0.6, alpha=0.8, zorder=4)
    marsh.plot(ax=ax, facecolor=C["marsh"], edgecolor=C["contour_light"], linewidth=0, zorder=4)
    parks.plot(ax=ax, facecolor=C["veg_fill"], edgecolor=C["veg"], linewidth=0.5, zorder=5)
    if level > 0:
        g = new[level]
        inside = g.geometry.iloc[0].intersection(city_g)  # the study area carries the colour
        outside = g.geometry.iloc[0].difference(city_g)
        gpd.GeoSeries([outside], crs=crs).plot(ax=ax, color=C["flood"], alpha=0.22, linewidth=0, zorder=6)
        gpd.GeoSeries([inside], crs=crs).plot(ax=ax, color=C["flood"], alpha=0.72, linewidth=0, zorder=6)
        gpd.GeoSeries([inside], crs=crs).boundary.plot(ax=ax, color=C["flood"], linewidth=0.3, alpha=0.8, zorder=6)
    flooded = bldg.index.isin(list(hit.get(level, ())))
    bldg[~flooded].plot(ax=ax, color=C["bldg"], linewidth=0, zorder=7)
    bldg[flooded].plot(ax=ax, color=C["flooded_bldg"], linewidth=0, zorder=7)
    gpd.GeoSeries(HL_FILL, crs=crs).plot(
        ax=ax, facecolor=pearl_lib.ACCENT, alpha=0.55, edgecolor="white", linewidth=1.2, zorder=7.4
    )
    bldg[HL_BLDG].plot(ax=ax, color=pearl_lib.ACCENT, edgecolor="white", linewidth=0.8, zorder=7.5)
    gpd.GeoSeries(HL_LINE, crs=crs).boundary.plot(ax=ax, color=pearl_lib.ACCENT, linewidth=1.1, alpha=0.9, zorder=7.6)
    city.boundary.plot(ax=ax, color=C["contour"], linewidth=0.9, linestyle=(0, (6, 3)), zorder=8)

    names = gpd.read_file("data/cache/tl_2025_12109_areawater.zip", columns=["FULLNAME"], ignore_geometry=True)
    for name, (x, y, rot) in WATER_LABELS.items():
        if name not in set(names["FULLNAME"]):
            continue
        text = " ".join(WORDS.get(w, w) for w in name.split())
        big = name == "Atlantic Ocean"
        ax.text(
            x,
            y,
            text,
            rotation=rot,
            ha="center",
            va="center",
            family=SERIF,
            style="italic",
            fontsize=16 if big else 11,
            color="#4F7C83" if not big else "white",
            zorder=10,
            alpha=0.95,
        )
    for name, (dx, dy) in SITE_LABELS.items():
        row = historic[historic["name"] == name]
        if row.empty:
            row = parks[parks["name"] == name]
        if row.empty:
            continue
        pt = row.geometry.iloc[0].representative_point()
        if (dx, dy) == (0, 0):  # area feature: label in place
            ax.text(
                pt.x + 150,
                pt.y + 300,
                name,
                family=SERIF,
                style="italic",
                fontsize=10.5,
                color=C["ink"],
                ha="center",
                va="center",
                rotation=72,
                zorder=11,
            )
            continue
        ax.annotate(
            name,
            xy=(pt.x, pt.y),
            xytext=(pt.x + dx, pt.y + dy),
            family=SERIF,
            style="italic",
            fontsize=10.5,
            color=C["ink"],
            ha="center",
            zorder=11,
            bbox=dict(boxstyle="square,pad=0.2", fc=C["paper"], ec="none", alpha=0.85),
            arrowprops=dict(arrowstyle="-", color=C["ink"], lw=0.5, shrinkA=1, shrinkB=1),
        )

    pearl_lib.draw(ax, PEARLS, level, lambda x, y: (x, y), PEARL_OFFSETS, size=0.85)

    # scale bar and north arrow, thin portfolio style
    bx, by = x0 + 250, y0 + 520
    for i in range(2):
        ax.add_patch(
            plt.Rectangle(
                (bx + i * 500, by),
                500,
                40,
                facecolor=C["ink"] if i == 0 else "white",
                edgecolor=C["ink"],
                lw=0.5,
                zorder=12,
            )
        )
    for d, t in ((0, "0"), (1000, "1 km")):
        ax.text(
            bx + d,
            by + 110,
            t,
            fontsize=8,
            color=C["ink"],
            ha="center",
            zorder=12,
            bbox=dict(boxstyle="square,pad=0.1", fc=C["paper"], ec="none"),
        )
    ax.add_patch(plt.Rectangle((bx - 120, by - 120), 1250, 360, fc=C["paper"], ec="none", alpha=0.8, zorder=11))
    nx, ny = bx + 1700, by - 10
    ax.annotate(
        "",
        xy=(nx, ny + 330),
        xytext=(nx, ny),
        zorder=12,
        arrowprops=dict(arrowstyle="-|>,head_width=0.22,head_length=0.55", color=C["ink"], lw=0.7),
    )
    ax.text(nx, ny + 370, "N", fontsize=8, color=C["ink"], ha="center", va="bottom", zorder=12)
    # fill the 1200 x 630 map band: full width, crop the height evenly
    crop = ((y1 - y0) - (x1 - x0) * (1 - CAPTION) * H / W) / 2
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0 + crop, y1 - crop)
    ax.set_axis_off()


def caption(fig, level):
    cap = fig.add_axes([0.05, 0.0, 0.9, CAPTION])
    cap.set_xlim(-0.3, 9.3)
    cap.set_ylim(0, 1)
    cap.set_axis_off()
    cap.plot([0, 2.6], [0.5, 0.5], color=C["muted"], lw=0.6, alpha=0.6)
    for lv in LEVELS:
        x = lv * 2.6 / 9
        on = lv <= level
        cap.scatter(
            [x],
            [0.5],
            s=40 if lv == level else 14,
            color=C["flood"] if on else "white",
            edgecolor=C["flood"],
            linewidth=0.8,
            zorder=3,
        )
        cap.text(x, 0.86, f"{lv}", ha="center", va="center", fontsize=8, color=C["ink"] if lv == level else C["muted"])
    cap.text(2.85, 0.5, "ft", va="center", fontsize=8, color=C["muted"])
    text = (
        "Today, at mean higher high water: tidal marsh (tan) is already under water"
        if level == 0
        else f"+{level} ft of sea-level rise: {pct[level]:.1f}% of St. Augustine's land newly flooded"
    )
    cap.text(9.3, 0.5, text, ha="right", va="center", fontsize=12.5, color=C["muted"])


def render(level, scale):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100 * scale, facecolor=C["paper"])
    ax = fig.add_axes([0, CAPTION, 1, 1 - CAPTION])
    # keep the map at true scale: fit the frame's aspect into the axes
    draw_map(ax, level)
    caption(fig, level)
    return fig


OUT.mkdir(parents=True, exist_ok=True)
paths = []
for lv in LEVELS:
    for scale, suffix in ((1, ""), (2, "@2x")):
        fig = render(lv, scale)
        path = OUT / f"frame_{lv}ft{suffix}.png"
        fig.savefig(path, dpi=100 * scale, facecolor=C["paper"], metadata={"Software": None})
        plt.close(fig)
        if scale == 1:
            paths.append(path)
    print("frame", lv)

frames = [Image.open(p).convert("RGB") for p in paths]
frames[0].save(OUT / "rise.gif", save_all=True, append_images=frames[1:], duration=1000, loop=0)
sheet = Image.new("RGB", (W, H * 3 // 2), "white")
for i, f in enumerate(frames):
    sheet.paste(f.resize((W // 2, H // 2)), ((i % 2) * W // 2, (i // 2) * H // 2))
sheet.save(OUT / "contact_sheet.png")
print("done")
