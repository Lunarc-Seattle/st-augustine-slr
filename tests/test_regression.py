"""Checks on the saved real-data window and a regression against its baseline."""

from pathlib import Path

import pandas as pd
import pytest

from slr import pipeline

FIXTURES = Path(__file__).parent / "fixtures"
# 1e-6 km² is 1 m²: far below the data's ~3 m grid, far above float noise.
TOLERANCE_KM2 = 1e-6
AREA_COLUMNS = ["land_km2", "inundated_land_km2", "already_at_baseline_km2", "new_inundation_km2"]


@pytest.fixture(scope="module")
def table(window):
    """Run the real land-loss code (including its self-checks) on the window."""
    cfg, flooded, land = window
    return pipeline.land_loss_table(cfg, flooded, land)


@pytest.mark.parametrize("kind", ["slr", "total"])
def test_inundated_area_never_shrinks(table, kind):
    """More sea-level rise can only flood more connected land."""
    values = table[table["kind"] == kind].sort_values("level_ft")["inundated_land_km2"]
    assert (values.diff().dropna() >= -TOLERANCE_KM2).all()


def test_new_loss_is_zero_at_baseline(table):
    assert (table[table["level_ft"] == 0]["new_inundation_km2"] == 0).all()


def test_total_is_sum_of_slr_and_low(table):
    by_kind = table.pivot(index="level_ft", columns="kind", values="new_inundation_km2")
    assert (by_kind["slr"] + by_kind["low"] - by_kind["total"]).abs().max() < TOLERANCE_KM2


def test_matches_saved_baseline(table):
    """Any change in method or libraries that moves results by > 1 m² fails here."""
    baseline = pd.read_csv(FIXTURES / "baseline_land_loss.csv")
    current = table.reset_index(drop=True)
    assert list(current[["level_ft", "kind"]].itertuples(index=False)) == list(
        baseline[["level_ft", "kind"]].itertuples(index=False)
    )
    for column in AREA_COLUMNS:
        diff = (current[column] - baseline[column]).abs().max()
        assert diff < TOLERANCE_KM2, f"{column} differs by {diff} km²"
