"""Download cache, OSM query capture, manifest and CLI, all without the network."""

import json
import logging

import pytest

from slr import cli, download, manifest, osm


class FakeResponse:
    """Just enough of ``requests.Response`` for :func:`download.fetch`."""

    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.body


def test_fetch_downloads_once_and_records_provenance(tmp_path, monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return FakeResponse(b"hello")

    monkeypatch.setattr(download.requests, "get", fake_get)
    url = "https://example.org/data/file.zip"
    path = download.fetch(url, cache_dir=tmp_path)
    again = download.fetch(url, cache_dir=tmp_path)

    assert path == again == tmp_path / "file.zip"
    assert calls == [url], "a cached file must not be downloaded again"
    meta = download.read_meta(path)
    assert meta["url"] == url
    assert meta["bytes"] == 5
    # SHA-256 of b"hello"
    assert meta["sha256"] == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
    assert not (tmp_path / "file.zip.part").exists()


def test_fetch_without_sidecar_downloads_again(tmp_path, monkeypatch):
    """A file with no .meta.json may be a leftover; it is never trusted."""
    (tmp_path / "file.zip").write_bytes(b"stale")
    monkeypatch.setattr(download.requests, "get", lambda url, **kw: FakeResponse(b"fresh"))
    path = download.fetch("https://example.org/file.zip", cache_dir=tmp_path)
    assert path.read_bytes() == b"fresh"


def test_query_recorder_keeps_overpass_query_text():
    recorder = osm._QueryRecorder()
    record = logging.LogRecord(
        "osmnx", logging.INFO, "", 0, "Post https://overpass/api?data=%5Bout%3Ajson%5D;", None, None
    )
    recorder.emit(record)
    recorder.emit(logging.LogRecord("osmnx", logging.INFO, "", 0, "Something else", None, None))
    assert recorder.queries == ["[out:json];"]


def test_git_commit_reports_a_hash():
    info = manifest.git_commit()
    assert len(info["commit"]) == 40
    assert isinstance(info["dirty"], bool)


def test_cli_rejects_unknown_command(capsys):
    with pytest.raises(SystemExit):
        cli.main(["bogus"])
    assert "invalid choice" in capsys.readouterr().err


def test_manifest_records_inputs_and_output_hashes(tmp_path):
    source = tmp_path / "source.zip"
    source.write_bytes(b"x")
    download.meta_path(source).write_text(json.dumps({"url": "u", "sha256": "s"}))
    output = tmp_path / "table.csv"
    output.write_text("a\n1\n")
    context = {
        "paths": {"src": source},
        "osm_meta": {"queried_utc": "t"},
        "cfg": {"levels_ft": [1], "all_levels_ft": [0, 1]},
        "out_dir": tmp_path,
    }
    data = json.loads(manifest.write_manifest(context, [output]).read_text())
    assert data["inputs"]["src"]["url"] == "u"
    assert data["outputs"]["table.csv"] == download.sha256(output)
    assert "all_levels_ft" not in data["config"]
