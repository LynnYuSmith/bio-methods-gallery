import sys
from pathlib import Path

# make the synthetic-data helper (examples/make_sample.py) importable from the tests
sys.path.insert(0, str(Path(__file__).resolve().parent / "examples"))
