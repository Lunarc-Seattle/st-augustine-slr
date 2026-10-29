"""Write a run record so anyone can tell exactly what produced the outputs."""

import json
import platform
import subprocess
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import pyogrio

from slr.download import read_meta, sha256

PACKAGES = ["geopandas", "pyogrio", "shapely", "pyproj", "pandas", "numpy", "osmnx", "matplotlib", "PyYAML", "requests"]


def git_commit():
    """Current commit, plus whether uncommitted changes could affect the run."""

    def git(*args):
        return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def write_manifest(context, output_files):
    """Collect config, inputs, outputs and environment into manifest.json."""
    inputs = {key: read_meta(path) for key, path in context["paths"].items()}
    inputs["osm"] = context["osm_meta"]
    manifest = {
        "run_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "config": {k: v for k, v in context["cfg"].items() if k != "all_levels_ft"},
        "inputs": inputs,
        "outputs": {Path(f).name: sha256(f) for f in sorted(output_files)},
        "python": platform.python_version(),
        "packages": {name: version(name) for name in PACKAGES},
        "gdal": pyogrio.__gdal_version_string__,
        "git": git_commit(),
    }
    path = context["out_dir"] / "manifest.json"
    path.write_text(json.dumps(manifest, indent=2) + "\n")
    return path
