"""'String of pearls': landmark markers along the shore for the cover figures.

Each pearl is an OSM site (name and location from data/cache/osm/osm_sites.geojson);
the level at which it first touches flooded land comes from outputs/sites_at_risk.csv.
A pearl turns blue once the water reaches its level. Icons are simple pictograms
so the place reads at a glance: star fort, flag, plaza tree, houses, cannon, lighthouse, dunes.
"""

import math

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib.path import Path

# OSM name -> (short label, icon); north to south along the shore
SITES = {
    "1513 Ponce Landing Memorial": ("Ponce de León landing, 1513", "flag"),
    "Castillo de San Marcos": ("Castillo de San Marcos", "fort"),
    "Plaza de la Constitución": ("Plaza de la Constitución", "tree"),
    "Lincolnville Historic District": ("Lincolnville Historic District", "houses"),
    "Oglethorpe Battery Park": ("Oglethorpe Battery", "cannon"),
    "Lighthouse Park": ("Lighthouse Park", "lighthouse"),
    "Anastasia State Park": ("Anastasia State Park", "dunes"),
}

# vermilion accent (clash colour): warm against the blue-green water, so the pearls never sink into it
ACCENT, PAPER, BROWN, RING, TEXT = "#E4472B", "#FFFFFF", "#8E6A4B", "#B08D6E", "#3B3F45"


def load(crs, risk_csv="outputs/sites_at_risk.csv"):
    """GeoDataFrame of the pearls with x, y (in crs), label, icon and first flood level."""
    sites = gpd.read_file("data/cache/osm/osm_sites.geojson").to_crs(crs)
    risk = pd.read_csv(risk_csv)
    first = risk.groupby(["osm_type", "osm_id"])["level_ft"].min()
    rows = []
    for name, (label, icon) in SITES.items():
        hit = sites[sites["name"] == name]
        if hit.empty:
            raise SystemExit(f"OSM site not found: {name}")
        row = hit.iloc[0]
        pt = row.geometry.representative_point()
        level = first.get((row["osm_type"], row["osm_id"]))
        rows.append(
            dict(
                name=name,
                label=label,
                icon=icon,
                x=pt.x,
                y=pt.y,
                geometry=row.geometry,
                historic=row.get("historic"),
                floods_at=None if pd.isna(level) else int(level),
            )
        )
    return pd.DataFrame(rows)


# ---- icons as marker paths (unit box -1..1) ---------------------------------
def _poly(pts):
    pts = [*list(pts), pts[0]]
    return Path(pts, [Path.MOVETO] + [Path.LINETO] * (len(pts) - 2) + [Path.CLOSEPOLY])


def _rect(x0, y0, x1, y1):
    return _poly([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _circle(cx, cy, r, n=24):
    return _poly([(cx + r * math.cos(t), cy + r * math.sin(t)) for t in np.linspace(0, 2 * math.pi, n, endpoint=False)])


def _icon_paths(kind):
    if kind == "fort":  # four-bastion star, like the Castillo's plan
        pts = []
        for i in range(8):
            a = math.pi / 4 + i * math.pi / 4
            r = 0.95 if i % 2 == 0 else 0.42
            pts.append((r * math.cos(a), r * math.sin(a)))
        return [_poly(pts)]
    if kind == "flag":
        return [_rect(-0.55, -0.85, -0.42, 0.85), _poly([(-0.42, 0.85), (0.65, 0.5), (-0.42, 0.15)])]
    if kind == "tree":
        return [_circle(0, 0.25, 0.55), _rect(-0.1, -0.85, 0.1, -0.2)]
    if kind == "houses":

        def house(dx, s):
            return _poly(
                [
                    (dx - 0.42 * s, -0.75),
                    (dx + 0.42 * s, -0.75),
                    (dx + 0.42 * s, 0.05 * s),
                    (dx, 0.5 * s),
                    (dx - 0.42 * s, 0.05 * s),
                ]
            )

        return [house(-0.38, 1.0), house(0.42, 0.8)]
    if kind == "cannon":
        barrel = _poly([(-0.85, -0.05), (0.7, 0.45), (0.8, 0.2), (-0.75, -0.35)])
        return [barrel, _circle(-0.25, -0.45, 0.35)]
    if kind == "lighthouse":
        return [
            _poly([(-0.32, -0.85), (0.32, -0.85), (0.18, 0.35), (-0.18, 0.35)]),
            _rect(-0.26, 0.4, 0.26, 0.62),
            _poly([(-0.3, 0.66), (0.3, 0.66), (0, 0.92)]),
        ]
    if kind == "dunes":
        return [
            _poly([(-0.95, -0.6), (-0.35, 0.25), (0.15, -0.25), (0.5, 0.05), (0.95, -0.6)]),
            _circle(0.45, 0.6, 0.22),
        ]
    raise ValueError(kind)


ICONS = {
    k: Path.make_compound_path(*_icon_paths(k))
    for k in ("fort", "flag", "tree", "houses", "cannon", "lighthouse", "dunes")
}


def highlight_areas(pearls, small_km2=0.05, point_buffer=60):
    """What to colour on the map for each pearl.

    Small sites (fort, plaza, park) are filled; large ones (district, state park) get an
    outline only; point sites take the buildings within point_buffer metres.
    Returns (fill geometries, outline geometries).
    """
    fill, outline = [], []
    for g in pearls["geometry"]:
        if g.geom_type in ("Point", "MultiPoint"):
            fill.append(g.buffer(point_buffer))
        elif g.area / 1e6 < small_km2:
            fill.append(g)
        else:
            outline.append(g)
    return fill, outline


def draw(
    ax,
    pearls,
    level,
    xy,
    label_offsets,
    size=1.0,
    z=20,
    string=True,
    label_fs=10.5,
    label_bg=0.8,
    pin=None,
    icons=False,
    show_level=True,
):
    """Draw the string, the pearls and their labels.

    xy(x, y) maps plan coordinates to axes data coordinates (identity for a plan,
    the projection for 2.5D). label_offsets: name -> (dx, dy) in points.
    """
    pts = np.array([xy(x, y) for x, y in zip(pearls["x"], pearls["y"], strict=False)], float)
    if string and len(pts) > 1:  # smooth thread through the pearls (Catmull-Rom)
        P = np.vstack([pts[0], pts, pts[-1]])
        curve = []
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for t in np.linspace(0, 1, 20, endpoint=False):
                t2, t3 = t * t, t * t * t
                curve.append(
                    0.5
                    * (
                        2 * p1
                        + (-p0 + p2) * t
                        + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                        + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
                    )
                )
        curve.append(pts[-1])
        curve = np.array(curve)
        ax.plot(
            curve[:, 0],
            curve[:, 1],
            color=RING,
            lw=1.0,
            alpha=0.8,
            linestyle=(0, (1, 2.5)),
            solid_capstyle="round",
            zorder=z,
        )
    for (px, py), (_, row) in zip(pts, pearls.iterrows(), strict=False):
        if pin is not None:  # 2.5D: a thin pin from the ground up to the pearl
            gx, gy = pin(row["x"], row["y"])
            ax.plot([gx, px], [gy, py], color=BROWN, lw=0.9, alpha=0.9, zorder=z)
            ax.scatter([gx], [gy], s=10, color=BROWN, linewidths=0, zorder=z)
        wet = row["floods_at"] is not None and level >= row["floods_at"]
        s = (560 if icons else 90) * size
        for k, a in ((2.3, 0.10), (1.7, 0.16)):  # soft halo
            ax.scatter([px], [py], s=s * k, color="white", alpha=a * 2.5, linewidths=0, zorder=z + 1)
        ax.scatter(
            [px],
            [py],
            s=s,
            color=ACCENT if wet else PAPER,
            edgecolors=ACCENT if icons else "white",
            linewidths=1.3,
            zorder=z + 2,
        )
        if icons:
            ax.scatter(
                [px],
                [py],
                s=s * 0.42,
                marker=ICONS[row["icon"]],
                color=PAPER if wet else ACCENT,
                linewidths=0,
                zorder=z + 3,
            )
        elif not wet:  # dry: white dot with a vermilion core
            ax.scatter([px], [py], s=s * 0.35, color=ACCENT, linewidths=0, zorder=z + 3)
        # pearl sheen
        if icons:
            ax.scatter(
                [px],
                [py],
                s=s * 0.05,
                color="white",
                alpha=0.9,
                linewidths=0,
                zorder=z + 4,
                transform=ax.transData + _offset(ax, -4.5 * size, 4.5 * size),
            )
        dx, dy = label_offsets.get(row["name"], (16, 0))
        ha = "left" if dx >= 0 else "right"
        when = f"floods at +{row['floods_at']} ft" if row["floods_at"] is not None else "not flooded by 9 ft"
        ax.annotate(
            row["label"],
            xy=(px, py),
            xytext=(dx, dy + 5 if show_level else dy),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=label_fs,
            family="Baskerville",
            style="italic",
            color=TEXT,
            zorder=z + 5,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none", alpha=label_bg),
        )
        if not show_level:  # names only, e.g. when the image itself stands for one level
            continue
        ax.annotate(
            when,
            xy=(px, py),
            xytext=(dx, dy - 8),
            textcoords="offset points",
            ha=ha,
            va="center",
            fontsize=label_fs * 0.78,
            color=ACCENT if wet else "#7A6A5A",
            fontweight="demibold" if wet else "normal",
            zorder=z + 5,
            bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=label_bg),
        )


def _offset(ax, dx_pt, dy_pt):
    from matplotlib.transforms import ScaledTranslation

    return ScaledTranslation(dx_pt / 72, dy_pt / 72, ax.figure.dpi_scale_trans)
