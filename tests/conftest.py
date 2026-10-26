"""Shared fixtures: a small real-data window saved in tests/fixtures."""

from pathlib import Path

import geopandas as gpd
import pyogrio
import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def window():
    """Land and flood geometries for a 1.5 km window, read from disk only."""
    path = FIXTURES / "window.gpkg"
    layers = [name for name, _ in pyogrio.list_layers(path)]
    land = gpd.read_file(path, layer="land").geometry.iloc[0]
    flooded = {}
    for layer in layers:
        if layer == "land":
            continue
        kind, level = layer.split("_")
        flooded[kind, int(level)] = gpd.read_file(path, layer=layer).geometry.iloc[0]
    levels = sorted({level for _, level in flooded})
    cfg = {"baseline_ft": 0, "levels_ft": levels[1:], "all_levels_ft": levels}
    return cfg, flooded, land
