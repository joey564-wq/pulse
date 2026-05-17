"""Loading service definitions from disk."""

import tomllib
from pathlib import Path


def load_services(path: Path) -> list[dict]:
    """Load the list of services from a TOML config file."""
    with path.open("rb") as f:
        config = tomllib.load(f)
    return config.get("services", [])
