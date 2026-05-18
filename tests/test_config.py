"""Tests for pulse.config."""

from pathlib import Path

from pulse.config import load_services


def test_load_services_reads_toml(tmp_path: Path) -> None:
    """Loading a known-good config file returns the expected services."""
    config_file = tmp_path / "services.toml"
    config_file.write_text(
        """
        [[services]]
        name = "test1"
        url = "https://one.test"

        [[services]]
        name = "test2"
        url = "https://two.test"
        """
    )

    services = load_services(config_file)
    assert len(services) == 2
    assert services[0]["name"] == "test1"
    assert services[1]["url"] == "https://two.test"


def test_load_services_empty_when_missing_key(tmp_path: Path) -> None:
    """If the file has no services table, return an empty list."""
    config_file = tmp_path / "services.toml"
    config_file.write_text("# no services here\n")
    assert load_services(config_file) == []