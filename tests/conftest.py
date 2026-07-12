"""Pytest configuration for abfuhrkalender tests."""
import sys
from pathlib import Path

# Add the src/abfuhrkalender directory to the Python path
SRC_DIR = Path(__file__).resolve().parent / "src" / "abfuhrkalender"
sys.path.insert(0, str(SRC_DIR))

import pytest


@pytest.fixture(autouse=True)
def use_db(db):
    pass