"""Unit tests on synthetic geometry, where the right answer is known exactly."""

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from slr import analysis, load


def test_area_of_one_km_square():
    """A 1000 m x 1000 m square in a metre CRS is exactly 1 km²."""
    assert analysis.area_km2(box(0, 0, 1000, 1000)) == pytest.approx(1.0)


def test_level_row_splits_baseline_and_new():
    """Land 4 km², flooded 2 km², of which 1 km² was already flooded today."""
    land = box(0, 0, 2000, 2000)
    flooded = box(0, 0, 2000, 1000)
    baseline = box(0, 0, 1000, 1000)
    row = analysis.level_row(3, "slr", flooded, baseline, land)
    assert row["inundated_land_km2"] == pytest.approx(2.0)
    assert row["already_at_baseline_km2"] == pytest.approx(1.0)
    assert row["new_inundation_km2"] == pytest.approx(1.0)
    assert row["new_loss_pct_of_land"] == pytest.approx(25.0)


def test_dissolve_does_not_double_count_overlaps():
    """Two overlapping 1 km² squares cover 1.5 km², not 2 km²."""
    squares = gpd.GeoSeries([box(0, 0, 1000, 1000), box(500, 0, 1500, 1000)])
    assert analysis.area_km2(analysis.dissolve(squares)) == pytest.approx(1.5)


def test_noaa_layer_names():
    """Config levels map onto NOAA's half-foot layer names."""
    assert load.noaa_layer("FL_NE", "slr", 3) == "FL_NE_slr_3_0ft"
    assert load.noaa_layer("FL_NE", "low", 0.5) == "FL_NE_low_0_5ft"


def test_sites_in_counts_touching_features():
    """A point inside and a park that only partly overlaps both count."""
    sites = gpd.GeoDataFrame(
        {"name": ["inside", "partly", "outside"]},
        geometry=[Point(10, 10), box(90, 0, 200, 50), Point(500, 500)],
    )
    hit = analysis.sites_in(sites, box(0, 0, 100, 100), 3, "slr")
    assert list(hit["name"]) == ["inside", "partly"]


def _table(new_by_level, kind="slr"):
    """Minimal land-loss table for exercising the checks."""
    return pd.DataFrame(
        {"level_ft": list(new_by_level), "kind": kind, "new_inundation_km2": list(new_by_level.values())}
    )


def test_checks_reject_nonzero_baseline():
    with pytest.raises(AssertionError, match="baseline"):
        analysis.check_results(_table({0: 0.1, 1: 0.2}), {}, baseline_ft=0)


def test_checks_reject_shrinking_slr():
    with pytest.raises(AssertionError, match="shrinks"):
        analysis.check_results(_table({0: 0.0, 1: 0.5, 3: 0.4}), {}, baseline_ft=0)


def test_checks_allow_shrinking_low():
    """'low' may shrink because NOAA reclassifies it as 'slr'."""
    analysis.check_results(_table({0: 0.0, 1: 0.5, 3: 0.4}, "low"), {}, baseline_ft=0)


def test_checks_reject_slr_low_overlap():
    with pytest.raises(AssertionError, match="overlap"):
        analysis.check_results(_table({0: 0.0}), {3: 0.01}, baseline_ft=0)
