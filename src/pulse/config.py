# src/pulse/config.py — add at top
import tomllib
from pathlib import Path

from pydantic import ValidationError

from .models import Service


class ConfigError(Exception):
    """Human-readable config problem; safe to print verbatim."""


def load_services(path: Path) -> list[Service]:
    try:
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ConfigError(f"Config file not found: {path}") from None
    except tomllib.TOMLDecodeError as e:
        raise ConfigError(f"Could not parse {path} as TOML: {e}") from e

    services_raw = raw.get("services", [])
    if not isinstance(services_raw, list):
        raise ConfigError(
            f"In {path}, [[services]] must be a list of tables, got {type(services_raw).__name__}"
        )

    out: list[Service] = []
    for i, item in enumerate(services_raw):
        try:
            out.append(Service.model_validate(item))
        except ValidationError as e:
            details = "; ".join(
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}" for err in e.errors()
            )
            raise ConfigError(f"In {path}, services[{i}]: {details}") from e
    return out
