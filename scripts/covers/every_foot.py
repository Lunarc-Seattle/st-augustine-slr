"""Land loss and sites at risk at every foot from 0 to 9, for the project page's rising-water player.

Same pipeline functions, same self-checks and the same NOAA, Census and OSM inputs as
`make run`; only the level list is longer. The odd levels must match outputs/land_loss.csv
exactly, so the page never shows two different numbers for one level.

Outputs: outputs/covers/land_loss_every_foot.csv, outputs/covers/sites_every_foot.csv and
outputs/covers/every_foot.gpkg (city, land and the flooded land per kind and level, for flood_map.py)

Run from the repo root after `make run`: PYTHONPATH=src .venv/bin/python scripts/covers/every_foot.py
"""

from pathlib import Path

import geopandas as gpd
import pandas as pd

from slr import osm, pipeline

OUT = Path("outputs/covers")
LEVELS = list(range(1, 10))

cfg = pipeline.read_config("scenarios.yaml")
cfg["levels_ft"] = LEVELS
cfg["all_levels_ft"] = sorted({cfg["baseline_ft"], *LEVELS})
paths = pipeline.fetch_sources(cfg)
city, water, land = pipeline.load_study_area(cfg, paths)
sites, _ = osm.fetch_sites(city, cfg["osm_tags"], endpoint=cfg.get("overpass_url"))
sites = gpd.clip(sites, city)
flooded = pipeline.load_flooding(cfg, paths, city, land)

table = pipeline.land_loss_table(cfg, flooded, land)  # runs analysis.check_results
risk = pipeline.sites_at_risk(cfg, flooded, sites)[["level_ft", "kind", *pipeline.SITE_COLUMNS]]

# the levels already published must come out identical
published = pd.read_csv("outputs/land_loss.csv")
key = ["level_ft", "kind"]
both = published.merge(table, on=key, suffixes=("_pub", "_new"), validate="one_to_one")
if len(both) != len(published):
    raise SystemExit("every_foot: published levels missing from the new table")
for col in ("inundated_land_km2", "new_inundation_km2", "new_loss_pct_of_land"):
    gap = (both[f"{col}_pub"] - both[f"{col}_new"]).abs().max()
    if gap > 1e-6:  # CSV rounding is 6 decimals
        raise SystemExit(f"every_foot: {col} differs from outputs/land_loss.csv by {gap}")

OUT.mkdir(parents=True, exist_ok=True)
pipeline.write_csv(table, OUT / "land_loss_every_foot.csv")
pipeline.write_csv(risk.sort_values(["level_ft", "kind", "osm_type", "osm_id"]), OUT / "sites_every_foot.csv")
gpkg = OUT / "every_foot.gpkg"
gpkg.unlink(missing_ok=True)
crs = cfg["area_crs"]
gpd.GeoDataFrame(geometry=list(city.geometry), crs=crs).to_file(gpkg, layer="city")
gpd.GeoDataFrame(geometry=[land], crs=crs).to_file(gpkg, layer="land")
rows = [(kind, level, geom) for (kind, level), geom in sorted(flooded.items())]
gpd.GeoDataFrame(
    {"kind": [r[0] for r in rows], "level_ft": [r[1] for r in rows]}, geometry=[r[2] for r in rows], crs=crs
).to_file(gpkg, layer="flooded")
print(OUT / "land_loss_every_foot.csv")
