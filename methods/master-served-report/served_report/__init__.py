"""served_report: serve one self-contained HDF5 experiment file over a small REST API."""
from .server import serve, open_master, make_handler

__all__ = ["serve", "open_master", "make_handler"]
