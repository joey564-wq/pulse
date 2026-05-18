from pathlib import Path
from typer.testing import CliRunner

from pulse.cli import app


def test_history_with_empty_db(tmp_path: Path):
    runner = CliRunner()
    db = tmp_path / "test.db"
    result = runner.invoke(app, ["history", "--db", str(db)])
    assert result.exit_code == 0
    assert "No records yet." in result.output