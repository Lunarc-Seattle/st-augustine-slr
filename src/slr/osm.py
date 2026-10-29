"""Fetch historic sites and parks from OpenStreetMap once, then reuse them.

OSM changes every day, so the first query is frozen in the cache together with
the exact Overpass query text and the time it was sent. Later runs read the
frozen copy, which keeps results reproducible.
"""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import geopandas as gpd
import osmnx as ox

from slr.download import sha256

KEEP_COLUMNS = ["osm_type", "osm_id", "name", "historic", "leisure", "geometry"]


class _QueryRecorder(logging.Handler):
    """Collect the Overpass queries that OSMnx logs before each HTTP request."""

    def __init__(self):
        super().__init__()
        self.queries = []

    def emit(self, record):
        message = record.getMessage()
        if message.startswith("Post "):
            url = message.split()[1]
            self.queries.append(parse_qs(urlparse(url).query)["data"][0])


def _query_overpass(polygon_wgs84, tags):
    """Run the OSMnx query and capture the Overpass QL it sends."""
    ox.settings.use_cache = False  # we keep our own frozen copy instead
    ox.settings.log_file = True  # makes OSMnx send its messages to the logger
    recorder = _QueryRecorder()
    logger = logging.getLogger(ox.settings.log_name)
    logger.addHandler(recorder)  # OSMnx then skips creating its own log file
    logger.setLevel(logging.INFO)  # the "Post <url>" message is INFO
    try:
        features = ox.features_from_polygon(polygon_wgs84, tags)
    finally:
        logger.removeHandler(recorder)
        ox.settings.log_file = False
    return features, recorder.queries


def fetch_sites(city, tags, cache_dir=Path("data/cache/osm"), endpoint=None):
    """Return OSM sites inside the city (in the city's CRS) plus query metadata.

    ``endpoint`` overrides the Overpass API URL, e.g. a mirror when the main
    server is busy. It only matters for the first, uncached query.
    """
    cache_dir = Path(cache_dir)
    data_path = cache_dir / "osm_sites.geojson"
    meta_path = cache_dir / "osm_sites.meta.json"
    if not data_path.exists() or not meta_path.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        if endpoint:
            ox.settings.overpass_url = endpoint
        polygon = city.to_crs("EPSG:4326").geometry.iloc[0]
        queried = datetime.now(UTC).isoformat(timespec="seconds")
        features, queries = _query_overpass(polygon, tags)
        features = features.reset_index().rename(columns={"element": "osm_type", "id": "osm_id"})
        for column in KEEP_COLUMNS:
            if column not in features:
                features[column] = None
        features[KEEP_COLUMNS].to_file(data_path, driver="GeoJSON")
        meta = {
            "endpoint": ox.settings.overpass_url,
            "tags": tags,
            "queried_utc": queried,
            "overpass_queries": queries,
            "feature_count": len(features),
            "sha256": sha256(data_path),
        }
        meta_path.write_text(json.dumps(meta, indent=2))
    sites = gpd.read_file(data_path).to_crs(city.crs)
    return sites, json.loads(meta_path.read_text())
