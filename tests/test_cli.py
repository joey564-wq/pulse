"""CLI integration tests."""
from pathlib import Path

from typer.testing import CliRunner

from pulse.cli import app


def test_history_with_empty_db(tmp_path: Path):
    """History on a fresh DB prints the empty-state message."""
    runner = CliRunner()
    db = tmp_path / "test.db"
    result = runner.invoke(app, ["history", "--db", str(db)])
    assert result.exit_code == 0
    assert "No records yet." in result.output


def test_run_then_history_round_trip(tmp_path: Path, httpx_mock):
    """After `pulse run`, `pulse history` shows the persisted check."""
    httpx_mock.add_response(url="https://example.com", status_code=200)

    runner = CliRunner()
    db = tmp_path / "test.db"
    config = tmp_path / "services.toml"
    config.write_text('[[services]]\nurl = "https://example.com"\n')

    run_result = runner.invoke(
        app, ["run", "--config", str(config), "--db", str(db)]
    )
    assert run_result.exit_code == 0
    assert "https://example.com" in run_result.output

    history_result = runner.invoke(app, ["history", "--db", str(db)])
    assert history_result.exit_code == 0
    assert "https://example.com" in history_result.output
    assert "ok=True" in history_result.output


def test_history_with_url_filter(tmp_path: Path, httpx_mock):
    """The --url flag filters history to that URL only."""
    httpx_mock.add_response(url="https://a.example.com", status_code=200)
    httpx_mock.add_response(url="https://b.example.com", status_code=200)

    runner = CliRunner()
    db = tmp_path / "test.db"
    config = tmp_path / "services.toml"
    config.write_text(
        '[[services]]\nurl = "https://a.example.com"\n'
        '[[services]]\nurl = "https://b.example.com"\n'
    )

    runner.invoke(app, ["run", "--config", str(config), "--db", str(db)])

    filtered = runner.invoke(
        app, ["history", "--db", str(db), "--url", "https://a.example.com"]
    )
    assert filtered.exit_code == 0
    assert "https://a.example.com" in filtered.output
    assert "https://b.example.com" not in filtered.output