"""Area and overlay calculations. All inputs must be in a metric CRS."""

import geopandas as gpd
import pandas as pd
from shapely.geometry import MultiPolygon

KINDS = ("slr", "low")  # NOAA: ocean-connected vs. unconnected low-lying


def area_km2(geometry):
    """Area of a shapely geometry in km² (CRS units must be metres)."""
    return geometry.area / 1e6


def dissolve(gdf):
    """Merge a layer into one geometry so overlaps are never counted twice."""
    if gdf.empty:
        return MultiPolygon()
    return gdf.union_all()


def level_row(level_ft, kind, flooded, baseline, land):
    """Split flooded land into 'already flooded at the baseline' and 'new'.

    ``flooded`` and ``baseline`` are geometries already clipped to land.
    'New' is a geometric difference rather than a subtraction of areas, so it
    can never come out as a tiny negative number from floating-point noise.
    """
    land_km2 = area_km2(land)
    total = area_km2(flooded)
    already = area_km2(flooded.intersection(baseline))
    new = area_km2(flooded.difference(baseline))
    return {
        "level_ft": level_ft,
        "kind": kind,
        "land_km2": land_km2,
        "inundated_land_km2": total,
        "already_at_baseline_km2": already,
        "new_inundation_km2": new,
        "new_loss_pct_of_land": 100 * new / land_km2,
    }


def sites_in(sites, flooded, level_ft, kind):
    """OSM features that touch the flooded area (a park counts if any part does)."""
    hit = sites[sites.intersects(flooded)]
    out = pd.DataFrame(hit.drop(columns="geometry"))
    out.insert(0, "kind", kind)
    out.insert(0, "level_ft", level_ft)
    return out


def total_rows(table):
    """Add a 'total' row per level. slr and low never overlap, so they sum."""
    sums = table.groupby("level_ft", as_index=False)[
        ["inundated_land_km2", "already_at_baseline_km2", "new_inundation_km2"]
    ].sum()
    sums["kind"] = "total"
    sums["land_km2"] = table["land_km2"].iloc[0]
    sums["new_loss_pct_of_land"] = 100 * sums["new_inundation_km2"] / sums["land_km2"]
    return pd.concat([table, sums[table.columns]], ignore_index=True)


def check_results(table, overlaps, baseline_ft, tol_km2=1e-9):
    """Self-checks that a run must pass before its outputs are trusted.

    1. At the baseline level nothing is 'new', by definition.
    2. 'slr' and 'total' new inundation never shrink as the sea rises.
       'low' may shrink: NOAA reclassifies low areas as 'slr' once the rising
       water connects them to the ocean.
    3. 'slr' and 'low' never overlap, which is what makes 'total' a plain sum.
    """
    base = table[table["level_ft"] == baseline_ft]
    if not (base["new_inundation_km2"].abs() < tol_km2).all():
        raise AssertionError("New inundation at the baseline level must be 0")
    for kind in ("slr", "total"):
        rows = table[table["kind"] == kind].sort_values("level_ft")
        if (rows["new_inundation_km2"].diff().dropna() < -tol_km2).any():
            raise AssertionError(f"New inundation shrinks with rising level ({kind})")
    for level_ft, overlap_km2 in overlaps.items():
        if overlap_km2 > tol_km2:
            raise AssertionError(f"slr and low overlap at {level_ft} ft")
