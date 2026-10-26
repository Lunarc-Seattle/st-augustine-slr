# One-command entry points. `make run test` reruns everything and checks it.
PYTHON ?= python3
VENV := .venv
PY := $(VENV)/bin/python
export PYTHONPATH := src

.PHONY: venv data run test fixture clean

venv: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PY) -m pip install --quiet --upgrade pip
	$(PY) -m pip install --quiet -r requirements.txt
	touch $@

## Download every source into data/cache (skips files already cached).
data: venv
	$(PY) -m slr.cli data

## Analysis, self-checks, CSVs, figures and manifest into outputs/.
run: venv
	$(PY) -m slr.cli run

## Offline tests on the small fixture in tests/fixtures.
test: venv
	$(PY) -m pytest -q

## Rebuild the test fixture and regression baseline (only on intended changes).
fixture: venv
	$(PY) scripts/make_fixture.py

## Delete outputs but keep the download cache.
clean:
	rm -rf outputs
