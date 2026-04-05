from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def tmp_key_file(tmp_path: Path):
    """Return a factory that writes a JSON key file and returns its path."""

    def _factory(keys: list[dict]) -> Path:
        p = tmp_path / "keys.json"
        p.write_text(json.dumps({"keys": keys}), encoding="utf-8")
        return p

    return _factory
