from pathlib import Path

import pytest

from sales_lab.cli import main
from sales_lab.config import Settings


@pytest.fixture(autouse=True)
def env(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    monkeypatch.setenv("SALES_LAB_INPUT", str(settings.input_path))
    monkeypatch.setenv("SALES_LAB_DB", str(settings.db_path))
    monkeypatch.setenv("SALES_LAB_OUTPUT", str(settings.output_dir))


def test_run_summary_report(capsys: pytest.CaptureFixture[str], settings: Settings) -> None:
    assert main(["run"]) == 0
    assert "loaded 3" in capsys.readouterr().out

    assert main(["summary"]) == 0
    assert "Revenue: 20.30 EUR" in capsys.readouterr().out

    assert main(["report"]) == 0
    assert (settings.output_dir / "category_report.csv").exists()


def test_missing_input_returns_error_code(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SALES_LAB_INPUT", str(tmp_path / "missing.csv"))

    assert main(["run"]) == 1
    assert "Error" in capsys.readouterr().err
