"""Cut a small window out of the cached real data for fast offline tests.

Run once (needs `make data`): writes tests/fixtures/window.gpkg and the
regression baseline tests/fixtures/baseline_land_loss.csv. Re-run it only when
a change in results is intended, and commit both files together.
"""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import box

from slr import pipeline

FIXTURES = Path("tests/fixtures")
# A 1.5 km square over downtown and the Castillo (UTM 17N metres).
WINDOW = box(469000, 3306500, 470500, 3308000)


def main():
    """Clip city, land and every flood layer to WINDOW and save them."""
    cfg = pipeline.read_config("scenarios.yaml")
    paths = pipeline.fetch_sources(cfg)
    city, _, land = pipeline.load_study_area(cfg, paths)
    window = city.copy()
    window["geometry"] = city.intersection(WINDOW)
    land = land.intersection(WINDOW)
    flooded = pipeline.load_flooding(cfg, paths, window, land)

    out = FIXTURES / "window.gpkg"
    out.unlink(missing_ok=True)
    gpd.GeoDataFrame(geometry=[land], crs=city.crs).to_file(out, layer="land")
    for (kind, level), geometry in flooded.items():
        layer = f"{kind}_{level}"
        gpd.GeoDataFrame(geometry=[geometry], crs=city.crs).to_file(out, layer=layer)

    table = pipeline.land_loss_table(cfg, flooded, land)
    pipeline.write_csv(table, FIXTURES / "baseline_land_loss.csv")


if __name__ == "__main__":
    main()
