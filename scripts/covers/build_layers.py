"""Cache the wide-frame cover layers in data/cache/covers/layers_wide.gpkg (EPSG:26917).

Unlike build_layers.py these are not clipped to the city: the frame takes in the
inlet, Anastasia Island and the ocean so the coastline reads as a whole.
water = Census area water (it includes the ocean inside the county)
marsh = land already under water at MHHW (NOAA 0 ft slr + low, minus Census water)
new_<ft> = land newly flooded at that level (NOAA slr + low, minus water and marsh)

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/build_layers.py
"""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from slr import analysis, load, pipeline

OUT = Path("data/cache/covers/layers_wide.gpkg")
FRAME = (465500, 3304100, 475500, 3309900)  # same as fetch_buildings.py
LEVELS = [1, 2, 3, 4, 5, 6, 7, 8, 9]

cfg = pipeline.read_config("scenarios.yaml")
paths = pipeline.fetch_sources(cfg)
crs = cfg["area_crs"]
frame = gpd.GeoDataFrame(geometry=[box(*FRAME)], crs=crs)
city = load.load_city(paths["tiger_places"], cfg["study_area"]["name"], cfg["study_area"]["statefp"], crs)

src = cfg["sources"]["noaa_slr"]
gpkg = load.noaa_gpkg_path(paths["noaa_slr"], src["member"])


def noaa(kind, level):
    return analysis.dissolve(load.read_clipped(gpkg, frame, load.noaa_layer(src["layer_prefix"], kind, level)))


census_water = analysis.dissolve(load.read_clipped(paths["tiger_water"], frame))
slr0 = noaa("slr", 0)
water = census_water
frame_geom = frame.geometry.iloc[0]
land = frame_geom.difference(water)
marsh = noaa("low", 0).union(slr0).difference(census_water)


def save(name, geom):
    gpd.GeoDataFrame(geometry=[geom], crs=crs).to_file(OUT, layer=name)


OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.unlink(missing_ok=True)
save("frame", frame_geom)
save("city", city.geometry.iloc[0])
save("water", water)
save("land", land)
save("marsh", marsh)
today = water.union(marsh)
for level in LEVELS:
    flooded = noaa("slr", level).union(noaa("low", level))
    save(f"new_{level}", flooded.difference(today))
    print("level", level)

sites = gpd.read_file("data/cache/osm/osm_sites.geojson").to_crs(crs)
sites = gpd.clip(sites, frame)
sites[sites["leisure"] == "park"].to_file(OUT, layer="parks")
sites[sites["historic"].notna()].to_file(OUT, layer="historic")
print("wrote", OUT)
