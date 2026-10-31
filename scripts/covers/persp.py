"""Perspective diorama: the old town seen low from over the Matanzas, water rising as volume.

The window is drawn as a slab of ground with its two front faces cut open. Water is
drawn at its own height: the sea (deep blue) and the newly flooded land (aqua) are
lifted to the scenario level, with vertical water faces along their edges and on the
cut faces, so the rise reads as volume. Buildings are white OSM footprints extruded to
building:levels x 3.5 m (untagged = 1 storey). One vertical exaggeration VZ applies to
buildings and water alike.

Outputs in scripts/covers/frames_diorama/: frame_<ft>ft.png, rise.gif, split_<ft>ft.png

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/diorama.py
"""

import math
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
from matplotlib.collections import PolyCollection
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from shapely.geometry import LineString, box

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, str(Path(__file__).parent))
import itertools

import pearls as pearl_lib

L = Path("data/cache/covers/layers_wide.gpkg")
OUT = Path("outputs/covers/persp")
LEVELS = [0, 1, 3, 5, 7, 9]
COMPARE_LEVELS = list(range(10))  # the page's player steps every foot (scripts/covers/every_foot.py)
EVERY_FOOT = Path("outputs/covers")
SPLIT_LEVEL = 7
W, H = 1200, 700
WINDOW = (468900, 3305900, 470650, 3308700)  # old town; the south and east cuts open onto the Matanzas
HEADING = math.radians(112)  # direction the camera looks (counter-clockwise from east): up the bayfront, NNW
CAM_DIST, CAM_H = 2200.0, 980.0  # metres back from the centre and above the ground
FOCAL = 1.0
VZ = 5.0
FT = 0.3048
SLAB = 9.0  # ground slab thickness below MHHW (m, before VZ)

C = dict(
    paper="#FFFFFF",
    ground="#F5F1E8",
    ground_city="#EFE7D8",
    roof="#FFFFFF",
    wall_l="#EFEBE4",
    wall_r="#DBD3C6",
    edge="#C8BFB0",
    sea="#8FB2B6",
    sea_face="#6E969C",
    flood="#18A7B5",
    flood_face="#0F7E8C",
    wet_wall="#7FD0D8",
    soil_top="#E2D3BC",
    soil="#C9B193",
    soil_edge="#A98F6F",
    veg="#7FA86F",
    veg_fill="#CFE2BF",
    marsh="#E9B9A0",
    navy="#0F6E7A",
    coral=pearl_lib.ACCENT,
    mark_roof="#EE6A4D",
    mark_l="#D8452A",
    mark_r="#B23620",
    text="#33393F",
)
if Path("/System/Library/Fonts/Avenir Next.ttc").exists():
    font_manager.fontManager.addfont("/System/Library/Fonts/Avenir Next.ttc")
    plt.rcParams["font.family"] = "Avenir Next"

window = box(*WINDOW)
cx, cy = 469820.0, 3307250.0  # look-at point: the bayfront between the Plaza and the Castillo
# heading measured counter-clockwise from east; the camera sits behind the look-at point
FWD = np.array([math.cos(HEADING), math.sin(HEADING)])
RIGHT = np.array([FWD[1], -FWD[0]])
CAM = np.array([cx, cy]) - FWD * CAM_DIST
PITCH = math.atan2(CAM_H, CAM_DIST)
cp, sp = math.cos(PITCH), math.sin(PITCH)


def project(x, y, z=0.0):
    """Pinhole camera at CAM (height CAM_H) looking at the centre; z exaggerated by VZ."""
    dx, dy = np.asarray(x, float) - CAM[0], np.asarray(y, float) - CAM[1]
    rx = dx * RIGHT[0] + dy * RIGHT[1]
    fy = dx * FWD[0] + dy * FWD[1]
    vz = np.asarray(z, float) * VZ - CAM_H
    depth = fy * cp - vz * sp
    up = fy * sp + vz * cp
    return FOCAL * rx / depth, FOCAL * up / depth


def cam_dist(x, y):
    return math.hypot(x - CAM[0], y - CAM[1])


def ring_xy(ring, z=0.0):
    x, y = np.asarray(ring.coords).T
    return np.column_stack(project(x, y, z))


def parts(geom):
    if geom.is_empty:
        return []
    return [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon"]


def polys_xy(geom, z=0.0, min_area=20):
    return [ring_xy(p.exterior, z) for p in parts(geom) if p.area > min_area]


def faces_toward_viewer(p):
    """Edges of a polygon's exterior whose outward normal points at the viewer."""
    pts = np.asarray(p.exterior.coords)
    if not p.exterior.is_ccw:
        pts = pts[::-1]
    for (x1, y1), (x2, y2) in itertools.pairwise(pts):
        nx, ny = (y2 - y1), -(x2 - x1)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if (CAM[0] - mx) * nx + (CAM[1] - my) * ny > 0:  # faces the camera
            yield x1, y1, x2, y2, (nx * RIGHT[0] + ny * RIGHT[1]) < 0


def quad(x1, y1, x2, y2, z0, z1):
    a, b = project([x1, x2], [y1, y2], z0), project([x1, x2], [y1, y2], z1)
    return np.array([[a[0][0], a[1][0]], [a[0][1], a[1][1]], [b[0][1], b[1][1]], [b[0][0], b[1][0]]])


def layer(name):
    return gpd.read_file(L, layer=name).geometry.iloc[0].intersection(window)


land, water, marsh = layer("land"), layer("water"), layer("marsh")
city_full = gpd.read_file(L, layer="city").geometry.iloc[0]
new = {lv: layer(f"new_{lv}").simplify(2) for lv in COMPARE_LEVELS if lv > 0}
parks = gpd.read_file(L, layer="parks")
parks = parks[parks.geom_type.isin(["Polygon", "MultiPolygon"])].clip(window).geometry.union_all()

bldg = gpd.read_file("data/frozen/osm_buildings.geojson").to_crs(26917)
bldg = bldg[bldg.intersects(window) & bldg.intersects(city_full)].copy()
bldg["h"] = pd.to_numeric(bldg["building:levels"], errors="coerce").fillna(1).clip(1, 12) * 3.5
bldg["depth"] = [cam_dist(g.centroid.x, g.centroid.y) for g in bldg.geometry]
bldg = bldg.sort_values("depth", ascending=False)  # far first

PEARLS = pearl_lib.load(26917)
PEARLS = PEARLS[
    [window.buffer(-60).contains(gpd.points_from_xy([x], [y])[0]) for x, y in zip(PEARLS.x, PEARLS.y, strict=False)]
].copy()
HL_FILL, HL_LINE = pearl_lib.highlight_areas(PEARLS)
HL_FILL_G = gpd.GeoSeries(HL_FILL, crs=26917).union_all()
HL_IDX = set(bldg.index[bldg.intersects(HL_FILL_G)])  # landmark buildings, drawn in the accent
# historic structures mapped as sites, not buildings (the Castillo): extrude their OSM outline
_forts = [g for g, h in zip(PEARLS.geometry, PEARLS.historic, strict=False) if h in ("castle", "fort") and g.area > 0]
if _forts:
    extra = gpd.GeoDataFrame({"h": [10.0] * len(_forts)}, geometry=_forts, crs=26917)  # Castillo walls ~10 m
    extra.index = [f"site{i}" for i in range(len(_forts))]
    extra["depth"] = [cam_dist(g.centroid.x, g.centroid.y) for g in extra.geometry]
    bldg = pd.concat([bldg[~bldg.intersects(gpd.GeoSeries(_forts, crs=26917).union_all())], extra])
    bldg = bldg.sort_values("depth", ascending=False)
    HL_IDX |= set(extra.index)
PIN_M = 30  # pearl height above ground (m, before VZ)
PEARL_OFFSETS = {
    "1513 Ponce Landing Memorial": (20, 4),
    "Castillo de San Marcos": (22, 12),
    "Plaza de la Constitución": (-22, 6),
    "Lincolnville Historic District": (22, 4),
    "Oglethorpe Battery Park": (20, 6),
}

table = pd.read_csv("outputs/land_loss.csv")
pct = table[table["kind"] == "total"].set_index("level_ft")["new_loss_pct_of_land"]

# the two cut faces of the slab: window edges facing the viewer
FRONT = list(faces_toward_viewer(window))


def add(ax, polys, face, edge="none", lw=0.0, alpha=1.0, z=1):
    if len(polys):
        ax.add_collection(PolyCollection(polys, facecolors=face, edgecolors=edge, linewidths=lw, alpha=alpha, zorder=z))


def cut_face_segments(geom, x1, y1, x2, y2):
    """Pieces of a window edge that run through geom (where water meets the cut)."""
    seg = LineString([(x1, y1), (x2, y2)]).intersection(geom.buffer(0.5))
    return [g for g in getattr(seg, "geoms", [seg]) if g.geom_type == "LineString" and g.length > 5]


def draw_scene(ax, level, with_pearls=True):
    ax.set_facecolor(C["paper"])
    wz = level * FT
    flood = new.get(level, window.buffer(-1e9) if False else None)

    # slab: soil cut faces, then a thin top band
    for x1, y1, x2, y2, left in FRONT:
        add(ax, [quad(x1, y1, x2, y2, -SLAB, 0)], C["soil"] if left else C["soil_top"], C["soil_edge"], 0.6, z=1)
        # water on the cut faces: sea from below MHHW up to the level, flood from ground up to the level
        for g in cut_face_segments(water, x1, y1, x2, y2):
            (a1, b1), (a2, b2) = g.coords[0], g.coords[-1]
            add(ax, [quad(a1, b1, a2, b2, -SLAB * 0.55, wz)], C["sea_face"], z=1.5)
        if flood is not None and wz > 0:
            for g in cut_face_segments(flood, x1, y1, x2, y2):
                (a1, b1), (a2, b2) = g.coords[0], g.coords[-1]
                add(ax, [quad(a1, b1, a2, b2, 0, wz)], C["flood_face"], z=1.5)

    # ground
    add(ax, polys_xy(land), C["ground"], z=2)
    add(ax, polys_xy(land.intersection(city_full)), C["ground_city"], z=2)
    add(ax, polys_xy(marsh), C["marsh"], z=2)
    add(ax, polys_xy(parks), C["veg_fill"], C["veg"], 0.4, z=2)

    # water volumes: vertical faces along viewer-facing edges, then the raised surface
    walls = []
    if flood is not None and wz > 0:
        for p in parts(flood):
            if p.area < 40:
                continue
            for x1, y1, x2, y2, _ in faces_toward_viewer(p):
                walls.append(quad(x1, y1, x2, y2, 0, wz))
    add(ax, walls, C["flood_face"], z=3)
    add(ax, polys_xy(water, wz), C["sea"], z=3.1)
    if flood is not None:
        add(ax, polys_xy(flood, wz), C["flood"], C["flood_face"], 0.25, alpha=0.92, z=3.2)

    # landmark ground and district outlines sit on top of the water, at the water level
    zl = wz if flood is not None else 0
    add(ax, polys_xy(HL_FILL_G.intersection(window), zl), C["coral"], alpha=0.85, z=3.5)
    for g in HL_LINE:
        for p in parts(g.intersection(window)):
            ax.plot(*ring_xy(p.exterior, zl).T, color=C["coral"], lw=1.6, alpha=0.95, zorder=3.6)

    hit = set(bldg.index[bldg.intersects(flood)]) if flood is not None else set()
    polys, faces = [], []
    for idx, row in bldg.iterrows():
        h, wet = row["h"], idx in hit
        mark = idx in HL_IDX
        for p in parts(row.geometry):
            for x1, y1, x2, y2, left in faces_toward_viewer(p):
                zw = min(wz, h) if wet else 0
                if zw > 0:
                    polys.append(quad(x1, y1, x2, y2, 0, zw))
                    faces.append(C["wet_wall"])
                polys.append(quad(x1, y1, x2, y2, zw, h))
                if mark:
                    faces.append(C["mark_l"] if left else C["mark_r"])
                else:
                    faces.append(C["wall_l"] if left else C["wall_r"])
            polys.append(ring_xy(p.exterior, h))
            faces.append(C["mark_roof"] if mark else C["roof"])
    ax.add_collection(PolyCollection(polys, facecolors=faces, edgecolors=C["edge"], linewidths=0.15, zorder=4))
    for idx in HL_IDX:  # open courtyards (the Castillo's plaza de armas): floor and inner walls
        if idx not in bldg.index:
            continue
        g, h = bldg.loc[idx, "geometry"], bldg.loc[idx, "h"]
        for p in parts(g):
            for ring in p.interiors:
                draw_courtyard(ax, ring, h, wz if idx in hit else 0)

    if with_pearls:
        draw_pearls(ax, PEARLS, level)
    lx0, lx1, ly0, ly1 = view_limits()
    ax.set_xlim(lx0, lx1)
    ax.set_ylim(ly0, ly1)
    ax.set_axis_off()
    # white veil in the lower-left corner for the headline
    yy, xx = np.mgrid[0:1:200j, 0:1:340j]
    a = np.clip((1 - np.hypot(xx / 0.48, yy / 0.36)) * 2.4, 0, 1) ** 0.9
    ax.imshow(
        np.dstack([np.ones_like(a)] * 3 + [a]),
        extent=(lx0, lx1, ly0, ly1),
        origin="lower",
        zorder=25,
        aspect="auto",
        interpolation="bilinear",
    )


def draw_courtyard(ax, ring, h, wz):
    from matplotlib.patches import Polygon as MplPolygon

    opening = MplPolygon(ring_xy(ring, h), closed=True, transform=ax.transData, facecolor="none", edgecolor="none")
    ax.add_patch(opening)
    floor = PolyCollection([ring_xy(ring, 0)], facecolors=C["ground_city"], edgecolors="none", zorder=4.1)
    floor.set_clip_path(opening)
    ax.add_collection(floor)
    pts = np.asarray(ring.coords)
    centre = np.array([ring.centroid.x, ring.centroid.y])
    walls = []
    for (x1, y1), (x2, y2) in itertools.pairwise(pts):
        n = np.array([y2 - y1, -(x2 - x1)])
        mid = np.array([(x1 + x2) / 2, (y1 + y2) / 2])
        if n @ (centre - mid) < 0:
            n = -n  # normal points into the courtyard
        if n @ (CAM - mid) > 0:
            continue  # inner walls facing the camera are hidden by the near wall top
        d = cam_dist(*mid)
        walls.append((d, quad(x1, y1, x2, y2, 0, h), C["mark_l"] if n @ RIGHT < 0 else C["mark_r"]))
    walls.sort(key=lambda t: -t[0])
    if wz > 0:
        water = PolyCollection([ring_xy(ring, wz)], facecolors=C["flood"], alpha=0.92, edgecolors="none", zorder=4.15)
        water.set_clip_path(opening)
        ax.add_collection(water)
    col = PolyCollection(
        [w[1] for w in walls], facecolors=[w[2] for w in walls], edgecolors=C["edge"], linewidths=0.15, zorder=4.2
    )
    col.set_clip_path(opening)
    ax.add_collection(col)


def view_limits():
    """Frame the town, not the slab: fit the projected buildings and pearls, let the near slab bleed off."""
    bx, by = project(bldg.geometry.centroid.x.values, bldg.geometry.centroid.y.values, 0)
    px, py = project(PEARLS.x.values, PEARLS.y.values, PIN_M)
    xs, ys = np.concatenate([bx, px]), np.concatenate([by, py])
    x0, x1 = np.quantile(xs, 0.01), np.quantile(xs, 0.99)
    y0, y1 = np.quantile(ys, 0.01), max(ys)
    w = max(x1 - x0, (y1 - y0) * W / H) * 1.32
    h = w * H / W
    mx, my = (x0 + x1) / 2 + w * 0.04, y1 + h * 0.10 - h / 2  # top pearl sits just under the top edge
    return mx - w / 2, mx + w / 2, my - h / 2, my + h / 2


PEARL_SHOW_LEVEL = True  # "floods at +N ft" under each name; off for the compare stills


def draw_pearls(ax, rows, level):
    pearl_lib.draw(
        ax,
        rows,
        level,
        lambda x, y: project(x, y, PIN_M),
        PEARL_OFFSETS,
        size=1.5,
        z=30,
        string=False,
        pin=lambda x, y: project(x, y, 0),
        label_bg=0.85,
        show_level=PEARL_SHOW_LEVEL,
    )


def headline(fig, level, x=0.04, right=False):
    ha, x = ("right", 1 - x) if right else ("left", x)
    big = "Today" if level == 0 else f"+{level} ft"
    fig.text(
        x, 0.14, big, fontsize=50, fontweight="bold", color=C["text"] if level == 0 else C["navy"], ha=ha, va="baseline"
    )
    if level == 0:
        fig.text(x, 0.085, "old town at mean higher high water", fontsize=13, color=C["text"], ha=ha)
    else:
        fig.text(x, 0.085, f"{pct[level]:.1f}%", fontsize=13, fontweight="bold", color=C["coral"], ha=ha)
        fig.text(
            x + (0.055 if not right else 0),
            0.085,
            " of the city's land newly under water" if not right else "",
            fontsize=13,
            color=C["text"],
            ha=ha,
        )
        if right:
            fig.text(x, 0.055, "of the city's land newly under water", fontsize=11, color=C["text"], ha=ha)


def credits(fig):
    fig.text(
        0.985,
        0.965,
        f"NOAA SLR Viewer · Census TIGER · OpenStreetMap   |   heights and water x{VZ:g}",
        ha="right",
        fontsize=7.5,
        color=C["text"],
        alpha=0.75,
    )


def render(level, with_text=True, with_pearls=True):
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=C["paper"])
    ax = fig.add_axes([0, 0, 1, 1])
    draw_scene(ax, level, with_pearls)
    if with_text:
        headline(fig, level)
        credits(fig)
    return fig


def save(fig, path):
    fig.savefig(path, dpi=100, facecolor=C["paper"], metadata={"Software": None})
    plt.close(fig)


def make_split():
    # split still: today | +SPLIT_LEVEL ft on a diagonal, pearls drawn last
    a_path, b_path = OUT / "_a.png", OUT / "_b.png"
    save(render(0, False, False), a_path)
    save(render(SPLIT_LEVEL, False, False), b_path)
    a, b = Image.open(a_path).convert("RGB"), Image.open(b_path).convert("RGB")
    # today: drained of colour, a little lighter, so the flooded half carries all the colour
    a = ImageEnhance.Brightness(ImageEnhance.Color(a).enhance(0.18)).enhance(1.04)
    mask = Image.new("L", (W, H), 0)
    x_top, x_bot = int(W * 0.47), int(W * 0.33)  # through the town, so both halves show streets
    ImageDraw.Draw(mask).polygon([(x_top, 0), (W, 0), (W, H), (x_bot, H)], fill=255)
    merged = Image.composite(b, a, mask)
    # divider: soft shadow, then a solid white blade
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).line([(x_top + 3, 0), (x_bot + 3, H)], fill=110, width=10)
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    merged = Image.composite(Image.new("RGB", (W, H), (20, 40, 45)), merged, shadow)
    ImageDraw.Draw(merged).line([(x_top, 0), (x_bot, H)], fill=(255, 255, 255), width=6)
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=C["paper"])
    ax = fig.add_axes([0, 0, 1, 1])
    lx0, lx1, ly0, ly1 = view_limits()
    ax.imshow(merged, extent=(lx0, lx1, ly0, ly1), aspect="auto")
    ax.set_xlim(lx0, lx1)
    ax.set_ylim(ly0, ly1)
    ax.set_axis_off()
    for i in range(len(PEARLS)):
        one = PEARLS.iloc[[i]]
        sx, sy = project(one.x.iloc[0], one.y.iloc[0], PIN_M)
        fx, fy = (sx - lx0) / (lx1 - lx0), (sy - ly0) / (ly1 - ly0)
        split_x = (x_bot + (x_top - x_bot) * fy) / W
        draw_pearls(ax, one, SPLIT_LEVEL if fx > split_x else 0)
    # slider handle in the middle of the blade, and tags at the top
    hx = (x_bot + (x_top - x_bot) * 0.5) / W
    hax = fig.add_axes([hx - 0.03, 0.5 - 0.03 * W / H, 0.06, 0.06 * W / H])
    hax.set_xlim(-1, 1)
    hax.set_ylim(-1, 1)
    hax.set_axis_off()
    hax.add_patch(plt.Circle((0, 0), 0.92, color="white", zorder=1))
    hax.add_patch(plt.Circle((0, 0), 0.92, fill=False, ec=C["coral"], lw=2.2, zorder=2))
    for sgn in (-1, 1):
        hax.add_patch(plt.Polygon([(sgn * 0.62, 0), (sgn * 0.22, 0.3), (sgn * 0.22, -0.3)], color=C["text"], zorder=3))
    tx = (x_bot + (x_top - x_bot) * 0.93) / W
    for text, dx, ha, fc, col in (
        ("TODAY", -0.012, "right", C["text"], "white"),
        (f"+{SPLIT_LEVEL} FT", 0.012, "left", C["coral"], "white"),
    ):
        fig.text(
            tx + dx,
            0.93,
            text,
            ha=ha,
            va="center",
            fontsize=10,
            fontweight="bold",
            color=col,
            bbox=dict(boxstyle="round,pad=0.45", fc=fc, ec="none"),
        )
    headline(fig, 0)
    headline(fig, SPLIT_LEVEL, right=True)
    credits(fig)
    save(fig, OUT / f"split_{SPLIT_LEVEL}ft.png")
    a_path.unlink()
    b_path.unlink()


# GIF timing (ms): start rising almost at once, keep each step short, hold longest on the worst case
HOLD_FIRST, HOLD_STEP, HOLD_LAST, TWEEN, TWEENS = 600, 650, 2600, 60, 5


def make_gif():
    imgs = [Image.open(OUT / f"frame_{lv}ft.png").convert("RGB") for lv in LEVELS]
    frames, durations = [], []
    for i, im in enumerate(imgs):
        frames.append(im)
        durations.append(HOLD_FIRST if i == 0 else HOLD_LAST if i == len(imgs) - 1 else HOLD_STEP)
        if i + 1 < len(imgs):
            for k in range(1, TWEENS + 1):
                frames.append(Image.blend(im, imgs[i + 1], k / (TWEENS + 1)))
                durations.append(TWEEN)
    frames[0].save(OUT / "rise.gif", save_all=True, append_images=frames[1:], duration=durations, loop=0, optimize=True)


def make_compare(scale=2):
    """Full-frame stills for the drag-to-compare slider on the project page.

    All stills keep full colour, so today reads as the same place, just drier; the aqua flood
    carries the contrast. Every foot from 0 to 9 is rendered for the page's player, with numbers
    and first-flood levels from scripts/covers/every_foot.py (odd levels equal land_loss.csv).
    levels.json carries the headline numbers.
    """
    import json

    global PEARL_SHOW_LEVEL
    out = OUT.parent / "compare"
    out.mkdir(parents=True, exist_ok=True)
    every = pd.read_csv(EVERY_FOOT / "land_loss_every_foot.csv")
    pct_every = every[every["kind"] == "total"].set_index("level_ft")["new_loss_pct_of_land"]
    first = pearl_lib.load(26917, EVERY_FOOT / "sites_every_foot.csv").set_index("name")["floods_at"]
    saved = PEARLS["floods_at"].copy()
    PEARLS["floods_at"] = [first[n] for n in PEARLS["name"]]
    PEARL_SHOW_LEVEL = False  # the page says which level each half shows
    for lv in COMPARE_LEVELS:
        tmp = out / "_tmp.png"
        fig = render(lv, with_text=False)
        if lv == 0:  # where each pearl sits in the still, as fractions from the top left, for the page's hotspots
            ax = fig.axes[0]
            to_frac = ax.transData + ax.transAxes.inverted()
            spots = {
                n: to_frac.transform(project(x, y, PIN_M))
                for n, x, y in zip(PEARLS["name"], PEARLS["x"], PEARLS["y"], strict=True)
            }
        fig.savefig(tmp, dpi=100 * scale, facecolor=C["paper"])
        plt.close(fig)
        im = Image.open(tmp).convert("RGB")
        tmp.unlink()
        im.save(out / ("today.jpg" if lv == 0 else f"{lv}ft.jpg"), quality=86, optimize=True, progressive=True)
        print("compare", lv)
    PEARL_SHOW_LEVEL = True
    PEARLS["floods_at"] = saved
    # floods_at: first level any flooded land touches the site; sea_at: first level the
    # ocean-connected (slr) water does. Earlier than sea_at means low-lying, unconnected ground.
    risk = pd.read_csv(EVERY_FOOT / "sites_every_foot.csv")
    sea = risk[risk["kind"] == "slr"].groupby("name")["level_ft"].min()

    def level_or_none(v):
        return None if v is None or pd.isna(v) else int(v)

    landmarks = [
        {
            "name": r["label"],
            "floods_at": level_or_none(first[r["name"]]),
            "sea_at": level_or_none(sea.get(r["name"])),
            "fx": round(float(spots[r["name"]][0]), 4),
            "fy": round(1 - float(spots[r["name"]][1]), 4),
        }
        for _, r in PEARLS.iterrows()
    ]
    levels = [{"ft": lv, "pct": round(float(pct_every[lv]), 1)} for lv in COMPARE_LEVELS if lv > 0]
    today_km2 = float(table[(table["kind"] == "total") & (table["level_ft"] == 0)]["inundated_land_km2"].iloc[0])
    # content hash of the stills: the page appends it to image URLs so browsers never show a stale level
    import hashlib

    digest = hashlib.sha256(b"".join(f.read_bytes() for f in sorted(out.glob("*.jpg")))).hexdigest()[:10]
    data = {
        "version": digest,
        "today_km2": round(today_km2, 2),
        "levels": levels,
        "landmarks": landmarks,
        "source": "outputs/covers/land_loss_every_foot.csv",
    }
    (out / "levels.json").write_text(json.dumps(data, indent=2))


if __name__ == "__main__":
    if sys.argv[1:] in (["split"], ["gif"], ["compare"]):
        {"split": make_split, "gif": make_gif, "compare": make_compare}[sys.argv[1]]()
        raise SystemExit
    OUT.mkdir(parents=True, exist_ok=True)
    only = [int(a) for a in sys.argv[1:]] or LEVELS
    paths = []
    for lv in only:
        p = OUT / f"frame_{lv}ft.png"
        save(render(lv), p)
        paths.append(p)
        print("frame", lv)
    if len(only) == len(LEVELS):
        make_gif()
        make_split()
        make_compare()
    print("done")
