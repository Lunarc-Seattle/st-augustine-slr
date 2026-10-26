"""Download source files once and remember where they came from.

Each cached file gets a sidecar ``<name>.meta.json`` with its URL, SHA-256 and
download date, so the run manifest can cite exactly what was analysed.
"""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import requests

CACHE_DIR = Path("data/cache")


def sha256(path):
    """Hash in 1 MB chunks so large files never have to fit in memory."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def meta_path(path):
    """Sidecar file that stores provenance for a cached download."""
    return path.with_name(path.name + ".meta.json")


def fetch(url, cache_dir=CACHE_DIR):
    """Return the local path of ``url``, downloading only if it is not cached.

    The file is written to ``.part`` first so an interrupted download is never
    mistaken for a complete one.
    """
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / url.rsplit("/", 1)[-1]
    if path.exists() and meta_path(path).exists():
        return path

    part = path.with_name(path.name + ".part")
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(part, "wb") as f:
            for chunk in response.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    part.rename(path)

    meta = {
        "url": url,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "downloaded_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    meta_path(path).write_text(json.dumps(meta, indent=2))
    return path


def read_meta(path):
    """Load the provenance record written by :func:`fetch`."""
    return json.loads(meta_path(Path(path)).read_text())
