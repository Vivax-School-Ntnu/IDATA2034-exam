"""Tests for persistent device identity."""

from pathlib import Path

from device.identity import load_or_create_uuid


def test_uuid_persistence(tmp_path: Path) -> None:
    """Test that the same UUID is reused."""
    path = tmp_path / "device_uuid.txt"

    first_uuid = load_or_create_uuid(path)
    second_uuid = load_or_create_uuid(path)

    assert first_uuid == second_uuid
    assert path.read_text(encoding="utf-8") == first_uuid
