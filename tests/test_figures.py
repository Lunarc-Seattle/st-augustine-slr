"""Smoke test: every figure draws on the fixture window and reruns byte-identically."""

import geopandas as gpd
import pytest
from shapely.geometry import Point, box

from slr import download, figures, pipeline

CRS = "EPSG:26917"
WINDOW = box(469000, 3306500, 470500, 3308000)  # same window as the fixture


@pytest.fixture(scope="module")
def context(window, tmp_path_factory):
    """A pipeline-like context built from the fixture instead of the full data."""
    cfg, flooded, land = window
    table = pipeline.land_loss_table(cfg, flooded, land)
    city = gpd.GeoDataFrame({"NAME": ["window"]}, geometry=[WINDOW], crs=CRS)
    water = gpd.GeoDataFrame(geometry=[WINDOW.difference(land)], crs=CRS)
    sites = gpd.GeoDataFrame(
        {
            "osm_type": ["node", "way", "node"],
            "osm_id": [1, 2, 3],
            "name": ["Site A", "Park B", None],
            "historic": ["fort", None, "memorial"],
            "leisure": [None, "park", None],
        },
        geometry=[Point(469700, 3307300), box(469100, 3306600, 469400, 3306900), Point(470300, 3307800)],
        crs=CRS,
    )
    risk = pipeline.sites_at_risk(cfg, flooded, sites)
    return {
        "cfg": cfg,
        "city": city,
        "water": water,
        "land": land,
        "sites": sites,
        "flooded": flooded,
        "table": table,
        "risk": risk,
        "out_dir": tmp_path_factory.mktemp("figures"),
    }


def test_all_figures_are_written_and_reproducible(context):
    first = figures.make_all(context)
    assert {p.suffix for p in first} == {".png", ".pdf"}
    assert all(p.stat().st_size > 0 for p in first)
    hashes = [download.sha256(p) for p in first]
    second = figures.make_all(context)
    assert [download.sha256(p) for p in second] == hashes
