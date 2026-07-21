"""Tests for served_report. Serve a sample master and check each endpoint's shape."""
import json
import sys
import threading
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))
from make_sample import make_sample                     # noqa: E402
from served_report import serve                         # noqa: E402


@pytest.fixture()
def base_url(tmp_path):
    master = str(tmp_path / "m.h5")
    make_sample(master, n_frames=120, n_rois=3)
    httpd = serve(master, port=8791)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:8791/api"
    httpd.shutdown()


def _get(url):
    return json.load(urllib.request.urlopen(url))


def test_info_lists_area_and_unit(base_url):
    info = _get(f"{base_url}/info")
    assert info["areas"] == ["Area1"]
    assert info["units"] == ["MUnit_0"]
    assert info["metadata"]["experiment_id"] == "sample"


def test_trace_matrix_and_single_roi(base_url):
    mat = _get(f"{base_url}/trace/MUnit_0/dff")
    assert mat["shape"] == [120, 3]
    assert mat["roi_names"] == ["Mean2", "Mean3", "Mean4"]
    col = _get(f"{base_url}/trace/MUnit_0/dff/Mean3")
    assert len(col["data"]) == 120


def test_rois_returns_polygons(base_url):
    rois = _get(f"{base_url}/rois/Area1")
    assert set(rois["polygons"]) == {"Mean2", "Mean3", "Mean4"}
    assert len(rois["polygons"]["Mean2"]) == 4        # square outline


def test_unknown_route_and_missing_key_are_404(base_url):
    for bad in ("nope", "trace/MUnit_0/missing", "rois/NoArea"):
        try:
            urllib.request.urlopen(f"{base_url}/{bad}")
            assert False, "expected an error status"
        except urllib.error.HTTPError as e:
            assert e.code == 404


def test_root_serves_html_report(base_url):
    import urllib.request
    root = base_url.replace("/api", "/")
    with urllib.request.urlopen(root) as r:
        assert r.headers["Content-Type"].startswith("text/html")
        body = r.read().decode()
    assert "<!doctype html>" in body.lower()
    assert "/api" in body                       # the report fetches the endpoints


def test_api_index_lists_endpoints(base_url):
    idx = _get(base_url)                          # /api
    assert idx["served"].endswith(".h5")
    assert idx["areas"] == ["Area1"]
    assert idx["endpoints"]["info"] == "/api/info"
