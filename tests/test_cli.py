import json
from pathlib import Path

from typer.testing import CliRunner

from siteledger.cli import app

runner = CliRunner()


def _write_project(tmp_path: Path, *, page_id: str = "alpha") -> Path:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps({"entries": [{"id": "alpha", "url": "pages/alpha.html"}]}),
        encoding="utf-8",
    )
    (tmp_path / "pages/alpha.html").write_text(
        f'<meta name="entry-id" content="{page_id}">',
        encoding="utf-8",
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/index.json]
  collection_path: entries
  id_field: id
  page_field: url
pages:
  include: [pages/*.html]
  id:
    selector: meta[name="entry-id"]
    attribute: content
""".strip(),
        encoding="utf-8",
    )
    return config_path


def test_cli_returns_zero_for_clean_site(tmp_path: Path) -> None:
    config_path = _write_project(tmp_path)

    result = runner.invoke(app, ["audit", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 0
    assert "No findings." in result.stdout
    assert "Scanned 1 record(s) and 1 HTML page(s)." in result.stdout


def test_cli_returns_one_when_error_findings_exist(tmp_path: Path) -> None:
    config_path = _write_project(tmp_path, page_id="different")

    result = runner.invoke(app, ["audit", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 1
    assert "ERROR SL003" in result.stdout
    assert "Summary: 1 errors" in result.stdout


def test_cli_returns_two_for_invalid_configuration(tmp_path: Path) -> None:
    bad_config = tmp_path / "siteledger.yml"
    bad_config.write_text("pages: {}", encoding="utf-8")

    result = runner.invoke(app, ["audit", str(tmp_path), "--config", str(bad_config)])

    assert result.exit_code == 2
    assert "SiteLedger error:" in result.stderr


def test_cli_returns_two_for_malformed_json(tmp_path: Path) -> None:
    config_path = _write_project(tmp_path)
    (tmp_path / "data/index.json").write_text('{"entries": [', encoding="utf-8")

    result = runner.invoke(app, ["audit", str(tmp_path), "--config", str(config_path)])

    assert result.exit_code == 2
    assert "invalid JSON" in result.stderr
    assert "line 1" in result.stderr
