"""Tests for methodname. Pin the behaviour the figure claims."""
import pytest

from methodname import run


def test_run_not_yet_implemented():
    with pytest.raises(NotImplementedError):
        run(None)

# Replace with real tests once run() is filled in:
#   - a known input gives a known output (the number the figure shows)
#   - the parameter moves the result in the stated direction
#   - an edge case (empty / single item / all-equal) is handled
