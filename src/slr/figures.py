"""A4 landscape figures: small-multiple maps, a land-loss chart, a sites map.

Every figure is saved as a 300-dpi PNG and a vector PDF. PDF metadata dates
are switched off so that a rerun writes byte-identical files.
"""

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")  # no screen needed; also makes CI and reruns identical
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402

A4_LANDSCAPE = (11.69, 8.27)  # inches
COLORS = {
    "land": "#f1efe8",
    "water": "#d6e1ea",
    "today": "#a9a8a2",  # land already flooded at the baseline (0 ft)
    "slr": "#2a78d6",    # newly flooded, ocean-connected
    "low": "#eb6834",    # newly flooded, unconnected low-lying
    "ink": "#0b0b0b",
    "muted": "#6f6e69",
    "park": "#1baf7a",
}
SOURCE = ("Sources: NOAA Office for Coastal Management Sea Level Rise Viewer data (FL_NE); "
          "U.S. Census Bureau TIGER/Line 2025 places and area water; "
          "© OpenStreetMap contributors (ODbL). NAD83 / UTM zone 17N.")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8, "svg.hashsalt": "slr"})


def save(fig, out_dir, name):
    """Write PNG (300 dpi) and PDF; return both paths for the manifest."""
    paths = [out_dir / f"{name}.png", out_dir / f"{name}.pdf"]
    fig.savefig(paths[0], dpi=300, metadata={"Software": None})
    fig.savefig(paths[1], metadata={"CreationDate": None, "Creator": None, "Producer": None})
    plt.close(fig)
    return paths


def source_line(fig, text=SOURCE):
    """Small grey credit line along the bottom edge of the page."""
    fig.text(0.01, 0.012, text, fontsize=6, color=COLORS["muted"])


def scale_bar(ax, length_m=2000):
    """Two-segment bar in map units (metres) at the lower left of the axes."""
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    x, y = x0 + 0.05 * (x1 - x0), y0 + 0.04 * (y1 - y0)
    height = 0.012 * (y1 - y0)
    half = length_m / 2
    ax.add_patch(Rectangle((x - 0.02 * (x1 - x0), y - 0.015 * (y1 - y0)), length_m + 0.06 * (x1 - x0),
                           0.07 * (y1 - y0), facecolor="white", alpha=0.85, lw=0, zorder=4))
    ax.add_patch(Rectangle((x, y), half, height, facecolor=COLORS["ink"], edgecolor=COLORS["ink"], lw=0.5, zorder=5))
    ax.add_patch(Rectangle((x + half, y), half, height, facecolor="white", edgecolor=COLORS["ink"], lw=0.5, zorder=5))
    for offset, label in [(0, "0"), (half, f"{half / 1000:g}"), (length_m, f"{length_m / 1000:g} km")]:
        ax.text(x + offset, y + 2.2 * height, label, ha="center", va="bottom", fontsize=6, zorder=5)


def north_arrow(ax):
    """Arrow pointing up. In UTM 17N here, grid north is within 0.2° of true north."""
    ax.annotate("N", xy=(0.92, 0.95), xytext=(0.92, 0.84), xycoords="axes fraction",
                ha="center", va="center", fontsize=8, fontweight="bold",
                arrowprops={"arrowstyle": "-|>", "color": COLORS["ink"], "lw": 1})


def finish_map(ax, scale_m=2000):
    """Scale bar, north arrow, and no axis labels (geopandas adds them per layer)."""
    ax.set_xlabel("")
    ax.set_ylabel("")
    scale_bar(ax, scale_m)
    north_arrow(ax)


def base_map(ax, ctx, bounds=None):
    """Land, water and city outline on a shared extent, without axes ticks."""
    gpd.GeoSeries([ctx["land"]], crs=ctx["city"].crs).plot(ax=ax, color=COLORS["land"], lw=0)
    ctx["water"].plot(ax=ax, color=COLORS["water"], lw=0)
    ctx["city"].boundary.plot(ax=ax, color=COLORS["ink"], lw=0.5)
    xmin, ymin, xmax, ymax = ctx["city"].total_bounds if bounds is None else bounds
    pad = 300
    ax.set_xlim(xmin - pad, xmax + pad)
    ax.set_ylim(ymin - pad, ymax + pad)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])


def flood_layers(ax, ctx, level):
    """Today's flooded land in grey, then new slr and new low on top."""
    flooded, base = ctx["flooded"], ctx["cfg"]["baseline_ft"]
    today = flooded["slr", base].union(flooded["low", base])
    crs = ctx["city"].crs
    gpd.GeoSeries([today], crs=crs).plot(ax=ax, color=COLORS["today"], lw=0)
    for kind in ("slr", "low"):
        new = flooded[kind, level].difference(today)
        if not new.is_empty:
            gpd.GeoSeries([new], crs=crs).plot(ax=ax, color=COLORS[kind], lw=0)


def legend_handles():
    return [
        Patch(color=COLORS["slr"], label="Newly inundated, ocean-connected (slr)"),
        Patch(color=COLORS["low"], label="Newly inundated, low-lying unconnected (low)"),
        Patch(color=COLORS["today"], label="Land already inundated at 0 ft (MHHW)"),
        Patch(color=COLORS["water"], label="Census water"),
        Patch(facecolor=COLORS["land"], edgecolor=COLORS["ink"], lw=0.5, label="City land"),
    ]


def loss_pct(table, level, kind="total"):
    row = table[(table["level_ft"] == level) & (table["kind"] == kind)]
    return float(row["new_loss_pct_of_land"].iloc[0])


def small_multiples(ctx):
    """One map per scenario level, same extent and scale, plus a legend panel."""
    levels = ctx["cfg"]["levels_ft"]
    columns = 3
    rows = -(-(len(levels) + 1) // columns)  # ceiling division; +1 for the legend
    fig, axes = plt.subplots(rows, columns, figsize=A4_LANDSCAPE)
    axes = axes.ravel()
    for ax, level in zip(axes, levels):
        base_map(ax, ctx)
        flood_layers(ax, ctx, level)
        ax.set_title(f"{level:g} ft sea-level rise: {loss_pct(ctx['table'], level):.1f}% of land newly inundated",
                     fontsize=8, loc="left")
        finish_map(ax)
    for ax in axes[len(levels):]:
        ax.axis("off")
    axes[len(levels)].legend(handles=legend_handles(), loc="center left", frameon=False, fontsize=8)
    fig.suptitle("St. Augustine, Florida: land inundated by sea-level rise above MHHW",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.91, bottom=0.04, wspace=0.03, hspace=0.14)
    source_line(fig)
    return save(fig, ctx["out_dir"], "fig1_inundation_small_multiples")


def land_loss_chart(ctx):
    """Stacked bars: newly inundated share of city land, slr and low apart."""
    table, levels = ctx["table"], ctx["cfg"]["levels_ft"]
    fig, ax = plt.subplots(figsize=A4_LANDSCAPE)
    x = range(len(levels))
    slr = [loss_pct(table, lv, "slr") for lv in levels]
    low = [loss_pct(table, lv, "low") for lv in levels]
    ax.bar(x, slr, width=0.6, color=COLORS["slr"], edgecolor="white", lw=1.5, label="Ocean-connected (slr)")
    ax.bar(x, low, width=0.6, bottom=slr, color=COLORS["low"], edgecolor="white", lw=1.5,
           label="Low-lying, unconnected (low)")
    for i, level in enumerate(levels):
        ax.text(i, slr[i] + low[i] + 1, f"{loss_pct(table, level):.1f}%", ha="center", fontsize=10)
    ax.set_xticks(list(x), [f"{lv:g} ft" for lv in levels], fontsize=10)
    ax.set_xlabel("Sea-level rise above mean higher high water (MHHW)", fontsize=10)
    ax.set_ylabel("Newly inundated land (% of city land area)", fontsize=10)
    ax.set_ylim(0, 100)
    ax.grid(axis="y", color="#e4e3df", lw=0.5)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.legend(frameon=False, fontsize=10, loc="upper left")
    land = table["land_km2"].iloc[0]
    ax.set_title(f"St. Augustine land loss by sea-level rise (city land = {land:.2f} km², "
                 "excluding land already inundated at 0 ft)", loc="left", fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.08, right=0.97, top=0.9, bottom=0.12)
    source_line(fig, SOURCE.replace(" © OpenStreetMap contributors (ODbL).", ""))
    return save(fig, ctx["out_dir"], "fig2_land_loss_by_level")


def downtown_bounds(points):
    """Zoom box around the middle 90% of historic sites, where most of them cluster."""
    x, y = points.x, points.y
    return (x.quantile(0.05), y.quantile(0.05), x.quantile(0.95), y.quantile(0.95))


def draw_sites(ax, ctx, level, hit):
    """Flood layers plus parks (outlines) and historic sites (markers)."""
    sites = ctx["sites"]
    historic, parks = sites["historic"].notna(), sites["leisure"] == "park"
    flood_layers(ax, ctx, level)
    sites[parks & ~hit].plot(ax=ax, facecolor="none", edgecolor=COLORS["muted"], lw=0.5)
    sites[parks & hit].plot(ax=ax, facecolor="none", edgecolor=COLORS["park"], lw=1, hatch="////")
    points = sites.representative_point()
    points[historic & ~hit].plot(ax=ax, color="white", edgecolor=COLORS["muted"], markersize=12, lw=0.6)
    points[historic & hit].plot(ax=ax, color=COLORS["ink"], marker="^", markersize=28)
    return points[historic]


def site_list(at_level, sites):
    """Text block naming the sites and parks at risk, with counts."""
    historic_rows = at_level[at_level["historic"].notna()]
    park_rows = at_level[at_level["leisure"] == "park"]
    lines = []
    for label, rows, total in [
        ("Historic sites at risk", historic_rows, int(sites["historic"].notna().sum())),
        ("Parks at risk", park_rows, int((sites["leisure"] == "park").sum())),
    ]:
        names = sorted(set(rows["name"].dropna()))
        lines.append(f"{label}: {rows['osm_id'].nunique()} of {total} ({len(names)} named)")
        lines += [f"  \u2022 {name}" for name in names] + [""]
    return "\n".join(lines)


def sites_map(ctx, level=3):
    """Historic sites and parks touched by flooded land at one level."""
    sites, risk = ctx["sites"], ctx["risk"]
    at_level = risk[risk["level_ft"] == level]
    hit = sites["osm_id"].isin(at_level["osm_id"])

    fig = plt.figure(figsize=A4_LANDSCAPE)
    city_ax = fig.add_axes([0.01, 0.05, 0.36, 0.84])
    zoom_ax = fig.add_axes([0.38, 0.05, 0.36, 0.84])
    base_map(city_ax, ctx)
    points = draw_sites(city_ax, ctx, level, hit)
    zoom = downtown_bounds(points)
    base_map(zoom_ax, ctx, bounds=zoom)
    draw_sites(zoom_ax, ctx, level, hit)
    city_ax.add_patch(Rectangle(zoom[:2], zoom[2] - zoom[0], zoom[3] - zoom[1],
                                fill=False, edgecolor=COLORS["ink"], lw=0.8, ls="--"))
    city_ax.set_title("City", loc="left", fontsize=9)
    zoom_ax.set_title("Downtown (dashed box)", loc="left", fontsize=9)
    finish_map(city_ax)
    finish_map(zoom_ax, scale_m=500)

    handles = legend_handles()[:3] + [
        Line2D([], [], marker="^", ls="", color=COLORS["ink"], label="Historic site at risk"),
        Line2D([], [], marker="o", ls="", mfc="white", mec=COLORS["muted"], label="Historic site not at risk"),
        Patch(facecolor="none", edgecolor=COLORS["park"], hatch="////", label="Park at risk"),
        Patch(facecolor="none", edgecolor=COLORS["muted"], label="Park not at risk"),
    ]
    fig.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.76, 0.89), fontsize=7, frameon=False)
    fig.text(0.765, 0.64, site_list(at_level, sites), va="top", fontsize=6.5, linespacing=1.35)
    fig.suptitle(f"Historic sites and parks touched by inundated land at {level:g} ft of sea-level rise",
                 x=0.01, ha="left", fontsize=12, fontweight="bold")
    source_line(fig)
    return save(fig, ctx["out_dir"], f"fig3_sites_at_risk_{level:g}ft")


def make_all(ctx):
    """Draw every figure; return the list of files written."""
    paths = small_multiples(ctx) + land_loss_chart(ctx)
    if 3 in ctx["cfg"]["levels_ft"]:
        paths += sites_map(ctx, 3)
    return paths
