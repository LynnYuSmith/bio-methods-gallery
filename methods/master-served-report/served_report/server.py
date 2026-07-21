"""Serve one self-contained HDF5 experiment file live over a small REST API.

The idea: a whole imaging experiment (traces, ROI geometry, per-area structure) lives in a single
HDF5 file with a fixed layout. A browser report reads its data on demand from a handful of `/api/*`
endpoints, so the file is the only thing you distribute. No sidecar files, no re-export, no database.

Layout the server expects (see `schema.py`):

    /metadata                     group, experiment attributes
    /groups/<area>                one group per imaging area
    /units/<unit>/traces/<kind>   (frames x rois) float array; kind in {dff, deconvolved, ...}
    /units/<unit>/roi_names       string dataset, column order of the traces
    /groups/<area>/polygons/<roi> (n, 2) float, ROI outline in pixels

Endpoints:

    GET /api/info                          areas, and the units under each
    GET /api/trace/<unit>/<kind>           the (frames x rois) matrix as JSON
    GET /api/trace/<unit>/<kind>/<roi>     one ROI column as JSON
    GET /api/rois/<area>                   ROI polygons for an area

The handle is cached on (path, mtime), so rewriting the file under a running server serves fresh
bytes on the next request instead of a stale cached handle.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import h5py
import numpy as np


@lru_cache(maxsize=4)
def _open(path: str, mtime: float) -> h5py.File:
    return h5py.File(path, "r")


def open_master(path: str) -> h5py.File:
    """Open the master read-only, cached on (path, mtime) so a rewrite invalidates the handle."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = 0.0
    return _open(path, mtime)


def _info(f: h5py.File) -> dict:
    """Areas and the units under each, read from the file structure."""
    areas = sorted(a for a in f.get("groups", {}))
    units = sorted(u for u in f.get("units", {}))
    meta = f["metadata"].attrs if "metadata" in f else f.attrs
    return {"areas": areas, "units": units,
            "metadata": {k: _scalar(v) for k, v in meta.items()}}


def _trace(f: h5py.File, unit: str, kind: str, roi: str | None) -> dict:
    """One trace matrix (frames x rois), or a single ROI column when `roi` is given."""
    ds = f[f"units/{unit}/traces/{kind}"]
    names = [n.decode() if isinstance(n, bytes) else n
             for n in f.get(f"units/{unit}/roi_names", [])[:]]
    if roi is None:
        return {"unit": unit, "kind": kind, "roi_names": names,
                "shape": list(ds.shape), "data": np.asarray(ds).tolist()}
    col = names.index(roi)
    return {"unit": unit, "kind": kind, "roi": roi, "data": np.asarray(ds[:, col]).tolist()}


def _rois(f: h5py.File, area: str) -> dict:
    """ROI polygons for an area, {roi_name: [[x, y], ...]}."""
    grp = f[f"groups/{area}/polygons"]
    return {"area": area,
            "polygons": {nm: np.asarray(grp[nm]).tolist() for nm in grp}}


def _scalar(v):
    if isinstance(v, bytes):
        return v.decode()
    if isinstance(v, np.generic):
        return v.item()
    return v


def make_handler(master_path: str):
    """A request handler bound to one master file. Routes `/api/*` to the readers above."""
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, payload: dict, code: int = 200) -> None:
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _report(self) -> None:
            """Serve the bundled HTML report; it reads the /api endpoints and draws the data."""
            html = (Path(__file__).resolve().parent / "report.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)

        def _index(self) -> None:
            """`/api` lists the endpoints, filled in with this file's real areas and units."""
            f = open_master(master_path)
            info = _info(f)
            area = info["areas"][0] if info["areas"] else "<area>"
            unit = info["units"][0] if info["units"] else "<unit>"
            self._send({
                "served": os.path.basename(master_path),
                "areas": info["areas"],
                "units": info["units"],
                "endpoints": {
                    "info": "/api/info",
                    "trace_matrix": f"/api/trace/{unit}/dff",
                    "trace_roi": f"/api/trace/{unit}/dff/<roi>",
                    "rois": f"/api/rois/{area}",
                },
            })

        def do_GET(self) -> None:
            parts = self.path.strip("/").split("/")
            if parts == [""]:
                self._report()                       # the root serves the HTML report
                return
            if parts[:1] != ["api"]:
                self._send({"error": "not found", "try": "/api"}, 404)
                return
            f = open_master(master_path)
            try:
                route = parts[1:]
                if route == []:
                    self._index()                    # /api lists the endpoints
                elif route == ["info"]:
                    self._send(_info(f))
                elif route[:1] == ["trace"] and len(route) in (3, 4):
                    self._send(_trace(f, route[1], route[2],
                                      route[3] if len(route) == 4 else None))
                elif route[:1] == ["rois"] and len(route) == 2:
                    self._send(_rois(f, route[1]))
                else:
                    self._send({"error": "unknown route", "path": self.path}, 404)
            except (KeyError, ValueError, IndexError) as e:
                self._send({"error": str(e), "path": self.path}, 404)

    return Handler


def serve(master_path: str, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Start a server for `master_path`. Returns the server; call `serve_forever()` or close it."""
    return ThreadingHTTPServer((host, port), make_handler(master_path))
