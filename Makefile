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

.PHONY: venv data run test lint format fixture clean

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

## Rebuild the test fixture and regression baseline (only on intended changes).
fixture: venv
	$(PY) scripts/make_fixture.py

## Delete outputs but keep the download cache.
clean:
	rm -rf outputs
