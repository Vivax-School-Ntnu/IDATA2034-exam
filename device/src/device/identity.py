"""Manage persistent device identity."""

from pathlib import Path
from uuid import uuid4


def load_or_create_uuid(path: Path) -> str:
    """Load an existing UUID or generate and save a new one."""
    if path.exists():
        return path.read_text(encoding="utf-8").strip()

    device_uuid = str(uuid4())
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(device_uuid, encoding="utf-8")
    return device_uuid
