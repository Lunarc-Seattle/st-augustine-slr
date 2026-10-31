"""Freeze OSM building footprints for the cover frame, with the Overpass query and time.

Same approach as src/slr/osm.py: query once, keep the result, the query text, the
time and a SHA-256 in data/frozen/osm_buildings.meta.json, and reuse the frozen copy after.

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/fetch_buildings.py
"""

import json
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from slr.download import sha256
from slr.osm import _query_overpass

FRAME = (465500, 3304100, 475500, 3309900)  # EPSG:26917 m, old town + inlet + Anastasia
TAGS = {"building": True}
KEEP = ["osm_type", "osm_id", "building", "height", "building:levels", "geometry"]
DATA = Path("data/frozen/osm_buildings.geojson")
META = Path("data/frozen/osm_buildings.meta.json")

if DATA.exists() and META.exists():
    raise SystemExit(f"{DATA} already frozen; delete it and the meta file to query again")

frame = gpd.GeoSeries([box(*FRAME)], crs="EPSG:26917").to_crs("EPSG:4326").iloc[0]
queried = datetime.now(UTC).isoformat(timespec="seconds")
features, queries = _query_overpass(frame, TAGS)
features = features.reset_index().rename(columns={"element": "osm_type", "id": "osm_id"})
features = features[features.geom_type.isin(["Polygon", "MultiPolygon"])]
for column in KEEP:
    if column not in features:
        features[column] = None
features[KEEP].to_file(DATA, driver="GeoJSON")
META.write_text(
    json.dumps(
        {
            "frame_epsg26917": FRAME,
            "tags": TAGS,
            "queried_utc": queried,
            "overpass_queries": queries,
            "feature_count": len(features),
            "sha256": sha256(DATA),
        },
        indent=2,
    )
)
print(len(features), "buildings ->", DATA)
