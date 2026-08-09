import sys
from pathlib import Path

# make the example helpers (make_sample) importable from tests, like the other tiles
sys.path.insert(0, str(Path(__file__).parent / "examples"))
