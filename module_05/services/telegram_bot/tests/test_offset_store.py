import tempfile
from pathlib import Path

from src import config, offset_store


def test_read_offset_returns_none_when_file_missing(monkeypatch):
    monkeypatch.setattr(config, "OFFSET_FILE_PATH", str(Path(tempfile.mkdtemp()) / "missing.txt"))
    assert offset_store.read_offset() is None


def test_write_then_read_offset_round_trips(monkeypatch):
    monkeypatch.setattr(config, "OFFSET_FILE_PATH", str(Path(tempfile.mkdtemp()) / "nested" / "offset.txt"))

    offset_store.write_offset(17)

    assert offset_store.read_offset() == 17
