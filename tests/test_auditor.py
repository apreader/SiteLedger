import json
from pathlib import Path

from siteledger.auditor import audit_site
from siteledger.config import load_config


def _write_config(tmp_path: Path) -> Path:
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


def _write_page(path: Path, identifier: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f'<html><head><meta name="entry-id" content="{identifier}"></head></html>',
        encoding="utf-8",
    )


def test_audit_clean_site_has_no_findings(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps({"entries": [{"id": "alpha", "url": "pages/alpha.html"}]}),
        encoding="utf-8",
    )
    _write_page(tmp_path / "pages/alpha.html", "alpha")

    result = audit_site(tmp_path, load_config(_write_config(tmp_path)))

    assert result.record_count == 1
    assert result.page_count == 1
    assert result.findings == ()
    assert result.has_errors is False


def test_audit_reports_missing_orphaned_and_mismatched_pages(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"id": "missing", "url": "pages/missing.html"},
                    {"id": "expected", "url": "pages/mismatch.html"},
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_page(tmp_path / "pages/mismatch.html", "actual")
    _write_page(tmp_path / "pages/orphan.html", "orphan")

    result = audit_site(tmp_path, load_config(_write_config(tmp_path)))

    assert [finding.rule_id for finding in result.findings] == ["SL001", "SL002", "SL003"]
    assert result.has_errors is True


def test_audit_reports_duplicate_record_ids_and_urls(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps(
            {
                "entries": [
                    {"id": "same", "url": "pages/one.html"},
                    {"id": "same", "url": "pages/one.html"},
                ]
            }
        ),
        encoding="utf-8",
    )
    _write_page(tmp_path / "pages/one.html", "same")

    result = audit_site(tmp_path, load_config(_write_config(tmp_path)))

    assert [finding.rule_id for finding in result.findings] == ["SL006", "SL006"]
