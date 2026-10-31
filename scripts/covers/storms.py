"""Tropical cyclones whose tracks passed near St. Augustine, 1851 to 2025, from NOAA's HURDAT2.

The centre is the city's TIGER/Line outline (its representative point). For each storm the
6-hourly track is turned into a line in UTM 17N and its closest approach measured to that
point; a storm counts when it passes within RADIUS_KM. Wind is the strongest 6-hourly value
recorded while the storm was inside the radius.

HURDAT2 holds tracks and winds only. The flood maps on this page are still water at a fixed
height; storm surge is not modelled anywhere in this project.

Outputs: outputs/covers/storms_near.csv and docs/figures/storms.json

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/storms.py
"""

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from slr import load, pipeline
from slr.download import fetch

HURDAT2 = "https://www.nhc.noaa.gov/data/hurdat/hurdat2-1851-2025-092326.txt"
RADIUS_KM = 100
OUT = Path("outputs/covers")
PAGE = Path("docs/figures/storms.json")


def category(wind_kt, status):
    """Saffir-Simpson category for hurricanes; TS / TD / other otherwise."""
    if status == "HU":
        for cat, low in ((5, 137), (4, 113), (3, 96), (2, 83)):
            if wind_kt >= low:
                return str(cat)
        return "1"
    return status if status in ("TS", "TD") else "other"


def read_hurdat2(path):
    """One DataFrame row per 6-hourly fix: storm id, name, time, status, lat, lon, wind (kt)."""
    rows, storm = [], None
    for line in Path(path).read_text().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if parts[0][:2].isalpha():  # header: AL011851, UNNAMED, 14,
            storm = (parts[0], parts[1].title())
            continue
        lat = float(parts[4][:-1]) * (1 if parts[4][-1] == "N" else -1)
        lon = float(parts[5][:-1]) * (-1 if parts[5][-1] == "W" else 1)
        rows.append(
            {
                "storm_id": storm[0],
                "name": storm[1],
                "time": pd.to_datetime(parts[0] + parts[1], format="%Y%m%d%H%M"),
                "status": parts[3],
                "lat": lat,
                "lon": lon,
                "wind_kt": int(parts[6]),
            }
        )
    return pd.DataFrame(rows)


cfg = pipeline.read_config("scenarios.yaml")
paths = pipeline.fetch_sources(cfg)
area = cfg["study_area"]
city = load.load_city(paths["tiger_places"], area["name"], area["statefp"], cfg["area_crs"])
centre = city.geometry.iloc[0].representative_point()

fixes = read_hurdat2(fetch(HURDAT2))
pts = gpd.GeoSeries(gpd.points_from_xy(fixes["lon"], fixes["lat"]), crs=4326).to_crs(cfg["area_crs"])
fixes["x"], fixes["y"] = pts.x.values, pts.y.values
fixes["km"] = [Point(x, y).distance(centre) / 1000 for x, y in zip(fixes["x"], fixes["y"], strict=True)]

storms = []
for sid, track in fixes.groupby("storm_id", sort=False):
    line = LineString(zip(track["x"], track["y"], strict=True)) if len(track) > 1 else Point(track[["x", "y"]].iloc[0])
    closest_km = line.distance(centre) / 1000
    if closest_km > RADIUS_KM:
        continue
    near = track.loc[track["km"].idxmin()]  # fix nearest the city, for the date
    inside = track[track["km"] <= RADIUS_KM]
    strongest = (inside if len(inside) else track.loc[[track["km"].idxmin()]]).sort_values("wind_kt").iloc[-1]
    storms.append(
        {
            "storm_id": sid,
            "name": track["name"].iloc[0],
            "year": int(near["time"].year),
            "date": near["time"].strftime("%Y-%m-%d"),
            "closest_km": round(closest_km, 1),
            "max_wind_kt": int(strongest["wind_kt"]),
            "category": category(int(strongest["wind_kt"]), strongest["status"]),
        }
    )

table = pd.DataFrame(storms).sort_values(["year", "date"]).reset_index(drop=True)
OUT.mkdir(parents=True, exist_ok=True)
table.to_csv(OUT / "storms_near.csv", index=False, lineterminator="\n")
PAGE.write_text(
    json.dumps(
        {
            "source": HURDAT2,
            "radius_km": RADIUS_KM,
            "first_year": int(fixes["time"].dt.year.min()),
            "last_year": int(fixes["time"].dt.year.max()),
            "storms": table.to_dict(orient="records"),
        },
        indent=1,
        ensure_ascii=False,
    )
    + "\n"
)
print(len(table), "storms within", RADIUS_KM, "km;", table["category"].value_counts().to_dict())
