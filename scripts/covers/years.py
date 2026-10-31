"""When could each level arrive? NOAA's 2022 sea-level-rise scenarios for St. Augustine.

Source: Sweet et al. 2022, NOAA Technical Report NOS 01, "SLR_TF U.S. Sea Level Projections.csv"
inside Sea_Level_Rise_Datasets_2022.zip. We take the report's 1-degree grid cell that contains
the city (its TIGER/Line representative point), all five scenarios, 17th/50th/83rd percentiles.

The file stores relative sea level in cm from 2005. The NOAA flood layers are heights above
MHHW on the 1983-2001 tidal epoch, centred on 1992, so each value gets the file's own
"Offset 1992 to 2000" plus "Offset 2000 to 2005" for that cell (note 5 of the file). Years
in between the file's decades are linear interpolation, so read them as "around".

Outputs: outputs/covers/years_crossing.csv and docs/figures/years.json

Run from the repo root: PYTHONPATH=src .venv/bin/python scripts/covers/years.py
"""

import csv
import io
import json
import zipfile
from pathlib import Path

import pandas as pd
from pyproj import Transformer

from slr import load, pipeline
from slr.download import fetch

# oceanservice.noaa.gov/hazards/sealevelrise/Sea_Level_Rise_Datasets_2022.zip redirects here
URL = "https://cdn.oceanservice.noaa.gov/oceanserviceprod/hazards/sealevelrise/Sea_Level_Rise_Datasets_2022.zip"
MEMBER = "SLR_TF U.S. Sea Level Projections.csv"
SCENARIOS = {"0.3": "Low", "0.5": "Intermediate-Low", "1.0": "Intermediate", "1.5": "Intermediate-High", "2.0": "High"}
LEVELS_FT = list(range(1, 10))
FT_CM = 30.48
OUT = Path("outputs/covers")
PAGE = Path("docs/figures/years.json")


def read_table(zip_path):
    with zipfile.ZipFile(zip_path) as z:
        name = next(n for n in z.namelist() if n.endswith(MEMBER))
        text = z.read(name).decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    head = next(i for i, r in enumerate(rows) if r and r[0] == "PSMSL Site")
    cols = [c for c in rows[head] if c]
    body = [r[: len(cols)] for r in rows[head + 1 :] if len(r) >= len(cols) and r[0]]
    return pd.DataFrame(body, columns=cols)


def crossing(years, values_cm, level_cm):
    """First year the series reaches level_cm, linearly interpolated; None if it never does."""
    for (y0, v0), (y1, v1) in zip(
        zip(years, values_cm, strict=True), zip(years[1:], values_cm[1:], strict=True), strict=False
    ):
        if v0 < level_cm <= v1:
            return round(y0 + (y1 - y0) * (level_cm - v0) / (v1 - v0))
    return None


cfg = pipeline.read_config("scenarios.yaml")
paths = pipeline.fetch_sources(cfg)
area = cfg["study_area"]
city = load.load_city(paths["tiger_places"], area["name"], area["statefp"], cfg["area_crs"])
pt = city.geometry.iloc[0].representative_point()
lon, lat = Transformer.from_crs(cfg["area_crs"], "EPSG:4326", always_xy=True).transform(pt.x, pt.y)

table = read_table(fetch(URL))
grid = table[table["PSMSL Site"].str.startswith("grid_")].copy()
grid["lat"] = grid["Lat"].astype(float)
grid["lon"] = ((grid["Long"].astype(float) + 180) % 360) - 180
cell = grid[((grid["lat"] - lat).abs() <= 0.5) & ((grid["lon"] - lon).abs() <= 0.5)]
if cell["PSMSL Site"].nunique() != 1:
    raise SystemExit(
        f"years: expected one grid cell around ({lat:.3f}, {lon:.3f}), found {cell['PSMSL Site'].unique()}"
    )
site = cell["PSMSL Site"].iloc[0]

year_cols = [c for c in table.columns if c.startswith("RSL") and c.endswith("(cm)") and c[3:7].isdigit()]
years = [int(c[3:7]) for c in year_cols]
offset = float(cell["Offset 1992 to 2000 (cm)"].iloc[0]) + float(cell["Offset 2000 to 2005 (cm)"].iloc[0])

series, rows = {}, []
for code, label in SCENARIOS.items():
    one = {}
    for pct in ("LOW", "MED", "HIGH"):
        row = cell[cell["Scenario"].str.replace(" ", "") == f"{code}-{pct}"]
        if len(row) != 1:
            raise SystemExit(f"years: {site} has no single row for {code} - {pct}")
        one[pct] = (row[year_cols].iloc[0].astype(float).to_numpy() + offset).tolist()
    series[label] = {
        "median_ft": [round(v / FT_CM, 3) for v in one["MED"]],
        "p17_ft": [round(v / FT_CM, 3) for v in one["LOW"]],
        "p83_ft": [round(v / FT_CM, 3) for v in one["HIGH"]],
    }
    for lv in LEVELS_FT:
        rows.append(
            {
                "scenario": label,
                "level_ft": lv,
                "year_median": crossing(years, one["MED"], lv * FT_CM),
                "year_83rd": crossing(years, one["HIGH"], lv * FT_CM),  # the faster end of the range
                "year_17th": crossing(years, one["LOW"], lv * FT_CM),
            }
        )
    series[label]["crossing"] = {r["level_ft"]: r["year_median"] for r in rows if r["scenario"] == label}

out = pd.DataFrame(rows)
OUT.mkdir(parents=True, exist_ok=True)
out.to_csv(OUT / "years_crossing.csv", index=False, lineterminator="\n")
PAGE.write_text(
    json.dumps(
        {
            "source": URL,
            "file": MEMBER,
            "cell": site,
            "cell_centre": [float(cell["lat"].iloc[0]), float(cell["lon"].iloc[0])],
            "offset_cm_1992_to_2005": offset,
            "years": years,
            "scenarios": series,
            "default": "Intermediate",
        },
        indent=1,
    )
    + "\n"
)
print(site, "offset", offset, "cm")
print(out.pivot(index="level_ft", columns="scenario", values="year_median").to_string())
