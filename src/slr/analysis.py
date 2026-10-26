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
    """
    land_km2 = area_km2(land)
    total = area_km2(flooded)
    already = area_km2(flooded.intersection(baseline))
    new = total - already
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


def check_results(table, baseline_ft):
    """Self-checks that a run must pass before its outputs are trusted.

    1. At the baseline level nothing is 'new', by definition.
    2. For each kind, new inundation never shrinks as the sea rises.
    """
    base = table[table["level_ft"] == baseline_ft]
    if not (base["new_inundation_km2"].abs() < 1e-9).all():
        raise AssertionError("New inundation at the baseline level must be 0")
    for kind, rows in table.groupby("kind"):
        values = rows.sort_values("level_ft")["new_inundation_km2"]
        if not values.is_monotonic_increasing:
            raise AssertionError(f"New inundation shrinks with rising level ({kind})")
