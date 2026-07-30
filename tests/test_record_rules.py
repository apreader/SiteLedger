from __future__ import annotations

import json
from pathlib import Path

from siteledger.auditor import audit_site
from siteledger.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "reconciliation"


def test_reconciliation_fixture_reports_all_expected_rule_classes() -> None:
    result = audit_site(FIXTURE, load_config(FIXTURE / "siteledger.yml"))

    assert [finding.rule_id for finding in result.findings] == [
        "SL001",
        "SL002",
        "SL003",
        "SL006",
        "SL006",
        "SL008",
        "SL009",
        "SL010",
        "SL011",
    ]
    assert result.record_count == 7
    assert result.page_count == 6
    assert all(finding.expected is not None for finding in result.findings)
    assert all(finding.actual is not None for finding in result.findings)
    assert all(finding.suggestion is not None for finding in result.findings)


def test_reconciliation_findings_preserve_field_and_line_locations() -> None:
    result = audit_site(FIXTURE, load_config(FIXTURE / "siteledger.yml"))
    by_rule = {
        finding.rule_id: finding for finding in result.findings if finding.rule_id != "SL006"
    }

    assert by_rule["SL001"].location == "$.entries[0].url"
    assert by_rule["SL008"].location == "$.entries[1].id"
    assert by_rule["SL009"].location == "$.entries[2].url"
    assert by_rule["SL003"].location == "line 2"
    assert by_rule["SL011"].location == "line 3"


def test_rule_switches_disable_only_selected_findings(tmp_path: Path) -> None:
    config_text = (FIXTURE / "siteledger.yml").read_text(encoding="utf-8")
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        config_text + "\nrules:\n  SL002: false\n  SL011: false\n",
        encoding="utf-8",
    )

    result = audit_site(FIXTURE, load_config(config_path))
    rule_ids = [finding.rule_id for finding in result.findings]

    assert "SL002" not in rule_ids
    assert "SL011" not in rule_ids
    assert "SL001" in rule_ids
    assert "SL009" in rule_ids


def test_duplicate_locations_are_deterministic_across_record_files(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/one.json").write_text(
        json.dumps([{"id": "same", "url": "pages/one.html"}]),
        encoding="utf-8",
    )
    (tmp_path / "data/two.json").write_text(
        json.dumps([{"id": "same", "url": "pages/two.html"}]),
        encoding="utf-8",
    )
    (tmp_path / "pages/one.html").write_text(
        '<meta name="entry-id" content="same">', encoding="utf-8"
    )
    (tmp_path / "pages/two.html").write_text(
        '<meta name="entry-id" content="same">', encoding="utf-8"
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/one.json, data/two.json]
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

    result = audit_site(tmp_path, load_config(config_path))
    duplicate_actuals = [
        finding.actual for finding in result.findings if finding.rule_id == "SL006"
    ]

    assert duplicate_actuals == [
        "data/one.json:$[0].id, data/two.json:$[0].id",
        "pages/one.html, pages/two.html",
    ]


def test_title_rule_is_inactive_when_record_title_field_is_omitted(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps([{"id": "alpha", "url": "pages/alpha.html", "title": "Expected"}]),
        encoding="utf-8",
    )
    (tmp_path / "pages/alpha.html").write_text(
        '<meta name="entry-id" content="alpha"><h1>Actual</h1>', encoding="utf-8"
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/index.json]
  id_field: id
  page_field: url
pages:
  include: [pages/*.html]
  id:
    selector: meta[name="entry-id"]
    attribute: content
  title:
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    result = audit_site(tmp_path, load_config(config_path))

    assert all(finding.rule_id != "SL011" for finding in result.findings)


def test_missing_page_field_is_reported_as_sl009(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps([{"id": "alpha"}]),
        encoding="utf-8",
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/index.json]
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

    result = audit_site(tmp_path, load_config(config_path))

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "SL009"
    assert result.findings[0].location == "$[0].url"
    assert result.findings[0].actual == "missing"


def test_missing_configured_record_title_is_reported_as_sl011(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps([{"id": "alpha", "url": "pages/alpha.html"}]),
        encoding="utf-8",
    )
    (tmp_path / "pages/alpha.html").write_text(
        '<meta name="entry-id" content="alpha"><h1>Alpha</h1>', encoding="utf-8"
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/index.json]
  id_field: id
  page_field: url
  title_field: title
pages:
  include: [pages/*.html]
  id:
    selector: meta[name="entry-id"]
    attribute: content
  title:
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    result = audit_site(tmp_path, load_config(config_path))

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "SL011"
    assert result.findings[0].file.as_posix() == "data/index.json"
    assert result.findings[0].location == "$[0].title"
    assert result.findings[0].actual == "missing"


def test_non_string_record_identifier_is_reported_as_sl008(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "pages").mkdir()
    (tmp_path / "data/index.json").write_text(
        json.dumps([{"id": 42, "url": "pages/alpha.html"}]),
        encoding="utf-8",
    )
    (tmp_path / "pages/alpha.html").write_text(
        '<meta name="entry-id" content="alpha">', encoding="utf-8"
    )
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  files: [data/index.json]
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

    result = audit_site(tmp_path, load_config(config_path))

    assert len(result.findings) == 1
    assert result.findings[0].rule_id == "SL008"
    assert result.findings[0].actual == "int: 42"
