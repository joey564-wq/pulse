import tomllib
from pathlib import Path

from .models import Service


def load_services(path: Path) -> list[Service]:
    """Load service definitions from a TOML file."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return [Service(**entry) for entry in data.get("services", [])]