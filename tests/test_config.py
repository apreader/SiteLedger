from pathlib import Path

import pytest

from siteledger.config import ConfigError, load_config


def test_load_config_parses_minimal_schema(tmp_path: Path) -> None:
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
  title:
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.records.files == ("data/index.json",)
    assert config.records.collection_path == "entries"
    assert config.pages.include == ("pages/*.html",)
    assert config.pages.exclude == ()
    assert config.pages.identifier.attribute == "content"
    assert config.pages.title is not None
    assert config.pages.title.selector == "h1"
    assert config.pages.title.attribute is None


def test_load_config_rejects_missing_record_files(tmp_path: Path) -> None:
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        """
records:
  id_field: id
  page_field: url
pages:
  include: [pages/*.html]
  id:
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="records.files"):
        load_config(config_path)


def test_load_config_preserves_cross_platform_patterns(tmp_path: Path) -> None:
    config_path = tmp_path / "siteledger.yml"
    config_path.write_text(
        r"""
records:
  files: [data/index.json]
  id_field: id
  page_field: url
pages:
  include: ["pages\\**\\*.html"]
  exclude: ["pages\\admin\\**"]
  id:
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.pages.include == (r"pages\**\*.html",)
    assert config.pages.exclude == (r"pages\admin\**",)


def test_load_config_allows_omitted_title_config(tmp_path: Path) -> None:
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
    selector: h1
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.pages.title is None


def test_load_config_parses_title_field_and_rule_switches(tmp_path: Path) -> None:
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
    selector: h1
rules:
  SL002: false
  SL011: true
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.records.title_field == "title"
    assert config.rules.is_enabled("SL001") is True
    assert config.rules.is_enabled("SL002") is False
    assert config.rules.is_enabled("SL011") is True


def test_load_config_rejects_unknown_rule_id(tmp_path: Path) -> None:
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
    selector: h1
rules:
  SL999: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="SL999"):
        load_config(config_path)


def test_load_config_rejects_non_boolean_rule_switch(tmp_path: Path) -> None:
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
    selector: h1
rules:
  SL001: disabled
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="rules.SL001"):
        load_config(config_path)


def test_load_config_rejects_non_string_rule_id(tmp_path: Path) -> None:
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
    selector: h1
rules:
  1: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="keys must be string"):
        load_config(config_path)
