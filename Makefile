# One-command entry points. `make run test` reruns everything and checks it.
# Works on Linux, macOS and Windows (Git Bash or any shell with GNU make).
ifeq ($(OS),Windows_NT)
PYTHON ?= python
BIN := Scripts
else
PYTHON ?= python3
BIN := bin
endif
VENV := .venv
PY := $(VENV)/$(BIN)/python

.PHONY: venv data run test lint format docs covers fixture clean

venv: $(VENV)/.installed

$(VENV)/.installed: requirements.txt pyproject.toml
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt
	$(PY) -m pip install --quiet --no-deps -e .
	touch $@

## Download every source into data/cache (skips files already cached).
data: venv
	$(PY) -m slr.cli data

## Analysis, self-checks, CSVs, figures, web map data and manifest into outputs/.
run: venv
	$(PY) -m slr.cli run

## Offline tests on the small fixture in tests/fixtures, with coverage.
test: venv
	$(PY) -m pytest -q --cov --cov-report=term-missing:skip-covered

## Lint and check formatting (what CI runs).
lint: venv
	$(PY) -m ruff check src tests scripts
	$(PY) -m ruff format --check src tests scripts

## Apply lint fixes and formatting.
format: venv
	$(PY) -m ruff check --fix src tests scripts
	$(PY) -m ruff format src tests scripts

## Copy the current figures into docs/ (README images and the project page).
docs:
	cp outputs/fig*.png docs/figures/
	cp outputs/fig[1-3]_*.pdf docs/pdf/

## Cover graphics (README and profile): plan + 2.5D frames, GIF, poster, and the project page's
## interactive data (every-foot levels, flood map, NOAA 2022 scenario years, HURDAT2 storms); needs `make run` first.
## Uses OSM building footprints and a LOC photo frozen in data/frozen/.
covers: venv
	$(PY) scripts/covers/build_layers.py
	$(PY) scripts/covers/every_foot.py
	$(PY) scripts/covers/flood_map.py
	$(PY) scripts/covers/years.py
	$(PY) scripts/covers/storms.py
	$(PY) scripts/covers/landmark_photos.py
	$(PY) scripts/covers/plan.py
	$(PY) scripts/covers/persp.py
	$(PY) scripts/covers/plan_photo.py
	$(PY) scripts/covers/poster.py
	cp outputs/covers/persp/rise.gif docs/figures/st-augustine-rise.gif
	cp outputs/covers/persp/split_7ft.png docs/figures/st-augustine-today-vs-7ft.png
	mkdir -p docs/figures/compare && cp outputs/covers/compare/* docs/figures/compare/
	cp outputs/covers/st-augustine-poster.png outputs/covers/st-augustine-plan.png docs/figures/

## Rebuild the test fixture and regression baseline (only on intended changes).
fixture: venv
	$(PY) scripts/make_fixture.py

## Delete outputs but keep the download cache.
clean:
	rm -rf outputs
