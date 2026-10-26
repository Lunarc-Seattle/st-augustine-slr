"""Run every scenario in the config and write the result tables."""

from pathlib import Path

import geopandas as gpd
import pandas as pd
import yaml

from slr import analysis, load, osm
from slr.download import fetch

SITE_COLUMNS = ["osm_type", "osm_id", "name", "historic", "leisure"]


def read_config(path):
    """Load scenarios.yaml; the baseline is always analysed with the levels."""
    cfg = yaml.safe_load(Path(path).read_text())
    cfg["all_levels_ft"] = sorted({cfg["baseline_ft"], *cfg["levels_ft"]})
    return cfg


def fetch_sources(cfg):
    """Download (or reuse) every file listed under ``sources``."""
    return {key: fetch(src["url"]) for key, src in cfg["sources"].items()}


def load_study_area(cfg, paths):
    """City outline, Census water inside it, and the land polygon."""
    area = cfg["study_area"]
    city = load.load_city(paths["tiger_places"], area["name"], area["statefp"], cfg["area_crs"])
    water = load.read_clipped(paths["tiger_water"], city)
    return city, water, load.land_polygon(city, water)


def load_flooding(cfg, paths, city, land):
    """Flooded land per (kind, level), each as one dissolved geometry."""
    src = cfg["sources"]["noaa_slr"]
    gpkg = load.noaa_gpkg_path(paths["noaa_slr"], src["member"])
    flooded = {}
    for kind in analysis.KINDS:
        for level in cfg["all_levels_ft"]:
            layer = load.noaa_layer(src["layer_prefix"], kind, level)
            polygons = load.read_clipped(gpkg, city, layer)
            flooded[kind, level] = analysis.dissolve(polygons).intersection(land)
    return flooded


def land_loss_table(cfg, flooded, land):
    """One row per level and kind, plus 'total' rows; checked before return.

    The baseline is all land flooded at baseline_ft, connected or not, because
    NOAA moves 'low' areas into 'slr' as the water rises; a per-kind baseline
    would count the same patch as 'new' once it changes class.
    """
    base = cfg["baseline_ft"]
    today = flooded["slr", base].union(flooded["low", base])
    rows = [
        analysis.level_row(level, kind, flooded[kind, level], today, land)
        for kind in analysis.KINDS
        for level in cfg["all_levels_ft"]
    ]
    table = analysis.total_rows(pd.DataFrame(rows))
    overlaps = {
        level: analysis.area_km2(flooded["slr", level].intersection(flooded["low", level]))
        for level in cfg["all_levels_ft"]
    }
    analysis.check_results(table, overlaps, base)
    return table.sort_values(["kind", "level_ft"]).reset_index(drop=True)


def sites_at_risk(cfg, flooded, sites):
    """Every historic site or park touched by flooded land, per level and kind."""
    tables = [
        analysis.sites_in(sites, flooded[kind, level], level, kind)
        for kind in analysis.KINDS
        for level in cfg["levels_ft"]
    ]
    return pd.concat(tables, ignore_index=True)


def write_csv(table, path):
    """Fixed rounding and row order so reruns produce byte-identical files."""
    table.to_csv(path, index=False, float_format="%.6f", lineterminator="\n")


def run(config_path="scenarios.yaml", out_dir="outputs"):
    """Full pipeline: data -> clip -> analysis -> checks -> CSV. Returns context."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    cfg = read_config(config_path)
    paths = fetch_sources(cfg)
    city, water, land = load_study_area(cfg, paths)
    sites, osm_meta = osm.fetch_sites(city, cfg["osm_tags"])
    sites = gpd.clip(sites, city)  # same footprint as every other layer
    flooded = load_flooding(cfg, paths, city, land)

    table = land_loss_table(cfg, flooded, land)
    risk = sites_at_risk(cfg, flooded, sites)[["level_ft", "kind", *SITE_COLUMNS]]
    write_csv(table, out_dir / "land_loss.csv")
    write_csv(risk.sort_values(["level_ft", "kind", "osm_type", "osm_id"]), out_dir / "sites_at_risk.csv")
    return {
        "cfg": cfg, "paths": paths, "city": city, "water": water, "land": land,
        "sites": sites, "osm_meta": osm_meta, "flooded": flooded, "table": table,
        "risk": risk, "out_dir": out_dir,
    }
