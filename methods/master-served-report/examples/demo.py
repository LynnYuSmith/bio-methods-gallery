"""Serve the sample master, then read a couple of endpoints and print them."""
import json
import threading
import urllib.request
from pathlib import Path

from served_report import serve
from make_sample import make_sample


def main() -> None:
    master = str(Path(__file__).resolve().parent / "sample_master.h5")
    make_sample(master)
    httpd = serve(master, port=8799)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    base = "http://127.0.0.1:8799/api"
    info = json.load(urllib.request.urlopen(f"{base}/info"))
    print("info:", info["areas"], info["units"])
    trace = json.load(urllib.request.urlopen(f"{base}/trace/MUnit_0/dff/Mean2"))
    print(f"trace MUnit_0/dff/Mean2: {len(trace['data'])} frames")
    rois = json.load(urllib.request.urlopen(f"{base}/rois/Area1"))
    print("rois Area1:", list(rois["polygons"]))
    httpd.shutdown()


if __name__ == "__main__":
    main()
