"""East-west cross-sections through the Castillo and the Plaza, for the project page.

Ground: USGS 3DEP elevations (NAVD88, m) from the Elevation Point Query Service, sampled every
STEP_M along each line and frozen in data/frozen/sections/ (later runs never query again).
Datum: NOAA CO-OPS station 8720576 "St. Augustine" (1983-2001 epoch, the epoch of the NOAA
flood layers); heights are shifted so 0 = mean higher high water (MHHW - NAVD88 from its datums).
Water: at each sample, NOAA's own first flood level and first sea (slr) level, read from
outputs/covers/every_foot.gpkg, so the section agrees with the maps; Census water is open water.

Output: docs/figures/sections.json

Run from the repo root after every_foot.py: PYTHONPATH=src .venv/bin/python scripts/covers/section.py
"""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests
from pyproj import Transformer
from shapely.geometry import Point

sys.path.insert(0, str(Path(__file__).parent))
import pearls as pearl_lib

from slr import load, pipeline

EPQS = "https://epqs.nationalmap.gov/v1/json"
STATION = "8720576"
DATUMS = f"https://api.tidesandcurrents.noaa.gov/mdapi/prod/webapi/stations/{STATION}/datums.json?units=metric"
FROZEN = Path("data/frozen/sections")
OUT = Path("docs/figures/sections.json")
STEP_M = 8.0
# each line runs west to east through a landmark: from the San Sebastian River side to Matanzas Bay
SECTIONS = {
    "castillo": ("Castillo de San Marcos", 1700.0, 700.0),
    "plaza": ("Plaza de la Constitución", 1500.0, 700.0),
}
LEVELS = list(range(10))

FROZEN.mkdir(parents=True, exist_ok=True)
to_ll = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)


def datums():
    path = FROZEN / f"coops_{STATION}_datums.json"
    if not path.exists():
        r = requests.get(DATUMS, timeout=60)
        r.raise_for_status()
        path.write_text(
            json.dumps({"url": DATUMS, "retrieved_utc": datetime.now(UTC).isoformat(), **r.json()}, indent=1)
        )
    d = json.loads(path.read_text())
    v = {x["name"]: float(x["value"]) for x in d["datums"]}
    return v["MHHW"] - v["NAVD88"], d["epoch"]


def elevations(name, xs, y):
    """3DEP ground elevation (NAVD88 m) at each x along the line, frozen to CSV on first run.

    The service times out now and then, so progress is checkpointed to a .part file and a
    rerun picks up where it stopped.
    """
    path = FROZEN / f"{name}_3dep.csv"
    if path.exists():
        return pd.read_csv(path)
    part = path.with_suffix(".part.csv")
    rows = pd.read_csv(part).to_dict("records") if part.exists() else []
    session = requests.Session()
    for x in xs[len(rows) :]:
        lon, lat = to_ll.transform(x, y)
        for attempt in range(12):
            try:
                r = session.get(EPQS, params={"x": lon, "y": lat, "wkid": 4326, "units": "Meters"}, timeout=40)
                r.raise_for_status()
                value = float(r.json()["value"])
                break
            except (requests.RequestException, ValueError, KeyError):
                time.sleep(min(30, 3 * (attempt + 1)))
        else:
            raise SystemExit(f"section: no elevation at {lon:.6f}, {lat:.6f}; rerun to resume")
        rows.append({"x": round(x, 1), "y": round(y, 1), "lon": round(lon, 7), "lat": round(lat, 7), "navd88_m": value})
        if len(rows) % 20 == 0:
            pd.DataFrame(rows).to_csv(part, index=False, lineterminator="\n")
    table = pd.DataFrame(rows)
    table.to_csv(path, index=False, lineterminator="\n")
    part.unlink(missing_ok=True)
    (FROZEN / f"{name}_3dep.meta.json").write_text(
        json.dumps(
            {
                "service": EPQS,
                "dataset": "USGS 3DEP",
                "units": "m, NAVD88",
                "step_m": STEP_M,
                "retrieved_utc": datetime.now(UTC).isoformat(),
            },
            indent=1,
        )
    )
    return table


mhhw_navd, epoch = datums()
src = Path("outputs/covers/every_foot.gpkg")
city = gpd.read_file(src, layer="city").geometry.union_all()
land = gpd.read_file(src, layer="land").geometry.iloc[0]
fl = gpd.read_file(src, layer="flooded")


def first(points, kinds):
    """First level (0-9) at which any of the given NOAA kinds floods each point; None if never."""
    out = [None] * len(points)
    for lv in LEVELS:
        g = fl[(fl["level_ft"] == lv) & fl["kind"].isin(kinds)].geometry.union_all()
        for i, p in enumerate(points):
            if out[i] is None and g.contains(p):
                out[i] = lv
    return out


cfg = pipeline.read_config("scenarios.yaml")
paths = pipeline.fetch_sources(cfg)
area = cfg["study_area"]
city_gdf = load.load_city(paths["tiger_places"], area["name"], area["statefp"], cfg["area_crs"])
water_named = load.read_clipped(paths["tiger_water"], city_gdf)
P = pearl_lib.load(26917, "outputs/covers/sites_every_foot.csv").set_index("name")

result = {"datum": {"station": STATION, "epoch": epoch, "mhhw_minus_navd88_m": round(mhhw_navd, 3)}, "sections": {}}
for key, (site, west, east) in SECTIONS.items():
    row = P.loc[site]
    cx, cy = row["x"], row["y"]
    n = int((west + east) / STEP_M) + 1
    xs = [cx - west + i * STEP_M for i in range(n)]
    elev = elevations(key, xs, cy)
    pts = [Point(x, cy) for x in elev["x"]]
    in_city = [city.contains(p) for p in pts]
    is_water = [not land.contains(p) and c for p, c in zip(pts, in_city, strict=True)]
    any_lv, sea_lv = first(pts, ["slr", "low"]), first(pts, ["slr"])

    def water_name(x, y=cy):
        hit = water_named[water_named.contains(Point(x, y))]
        return None if hit.empty or pd.isna(hit["FULLNAME"].iloc[0]) else hit["FULLNAME"].iloc[0]

    marks = [{"name": row["label"], "d": round(cx - xs[0], 1)}]
    for other, r2 in P.iterrows():
        if other != site and abs(r2["y"] - cy) < 60 and xs[0] < r2["x"] < xs[-1]:
            marks.append({"name": r2["label"], "d": round(r2["x"] - xs[0], 1)})
    result["sections"][key] = {
        "title": f"Through the {row['label']}" if not row["label"].startswith("Plaza") else "Through the Plaza",
        "landmark": row["label"],
        "step_m": STEP_M,
        "west_water": water_name(xs[0]),
        "east_water": water_name(xs[-1]),
        "marks": marks,
        "samples": [
            {
                "d": round(x - xs[0], 1),
                "z": round(z - mhhw_navd, 3),
                "city": c,
                "water": w,
                "first": a,
                "sea": s,
            }
            for x, z, c, w, a, s in zip(elev["x"], elev["navd88_m"], in_city, is_water, any_lv, sea_lv, strict=True)
        ],
    }
    print(key, len(xs), "samples;", result["sections"][key]["west_water"], "->", result["sections"][key]["east_water"])

OUT.write_text(json.dumps(result, separators=(",", ":"), ensure_ascii=False) + "\n")
print(OUT)
