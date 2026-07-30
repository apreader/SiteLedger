from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias

import yaml

from siteledger.rules.definitions import RULES


class ConfigError(ValueError):
    """Raised when a SiteLedger configuration file is missing or invalid."""


@dataclass(frozen=True, slots=True)
class RecordConfig:
    files: tuple[str, ...]
    collection_path: str | None
    id_field: str
    page_field: str
    title_field: str | None = None


@dataclass(frozen=True, slots=True)
class PageValueConfig:
    selector: str
    attribute: str | None


PageIdConfig: TypeAlias = PageValueConfig


@dataclass(frozen=True, slots=True)
class PageConfig:
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    identifier: PageValueConfig
    title: PageValueConfig | None = None


@dataclass(frozen=True, slots=True)
class RuleConfig:
    """Configured enablement state for stable SiteLedger rule IDs."""

    enabled: frozenset[str]

    def is_enabled(self, rule_id: str) -> bool:
        return rule_id in self.enabled


@dataclass(frozen=True, slots=True)
class SiteLedgerConfig:
    records: RecordConfig
    pages: PageConfig
    rules: RuleConfig


def _mapping(value: Any, key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"'{key}' must be a mapping")
    return value


def _required_string(mapping: dict[str, Any], key: str, section: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{section}.{key}' must be a non-empty string")
    return value.strip()


def _optional_string(mapping: dict[str, Any], key: str, section: str) -> str | None:
    value = mapping.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{section}.{key}' must be a non-empty string or null")
    return value.strip()


def _string_list(
    mapping: dict[str, Any],
    key: str,
    section: str,
    *,
    required: bool,
) -> tuple[str, ...]:
    value = mapping.get(key)
    if value is None and not required:
        return ()
    if not isinstance(value, list) or (required and not value):
        qualifier = "a non-empty" if required else "a"
        raise ConfigError(f"'{section}.{key}' must be {qualifier} list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ConfigError(f"'{section}.{key}' must contain only non-empty strings")
    return tuple(item.strip() for item in value)


def _page_value_config(value: Any, section: str) -> PageValueConfig:
    raw = _mapping(value, section)
    attribute = raw.get("attribute")
    if attribute is not None and (not isinstance(attribute, str) or not attribute.strip()):
        raise ConfigError(f"'{section}.attribute' must be a non-empty string or null")
    return PageValueConfig(
        selector=_required_string(raw, "selector", section),
        attribute=attribute.strip() if isinstance(attribute, str) else None,
    )


def _rule_config(value: Any) -> RuleConfig:
    if value is None:
        return RuleConfig(enabled=frozenset(RULES))
    raw = _mapping(value, "rules")
    if not all(isinstance(rule_id, str) for rule_id in raw):
        raise ConfigError("'rules' keys must be string rule IDs")
    unknown = sorted(set(raw) - set(RULES))
    if unknown:
        raise ConfigError(f"unknown rule ID(s) in 'rules': {', '.join(unknown)}")
    for rule_id, enabled in raw.items():
        if not isinstance(enabled, bool):
            raise ConfigError(f"'rules.{rule_id}' must be true or false")
    return RuleConfig(enabled=frozenset(rule_id for rule_id in RULES if raw.get(rule_id, True)))


def load_config(path: Path) -> SiteLedgerConfig:
    """Load and validate the intentionally small SiteLedger schema."""

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"configuration file does not exist: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"could not read configuration file: {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc

    root = _mapping(raw, "configuration")
    records_raw = _mapping(root.get("records"), "records")
    pages_raw = _mapping(root.get("pages"), "pages")

    collection_path = records_raw.get("collection_path")
    if collection_path is not None and not isinstance(collection_path, str):
        raise ConfigError("'records.collection_path' must be a string or null")

    title_raw = pages_raw.get("title")
    title_config = _page_value_config(title_raw, "pages.title") if title_raw is not None else None

    return SiteLedgerConfig(
        records=RecordConfig(
            files=_string_list(records_raw, "files", "records", required=True),
            collection_path=collection_path.strip() if isinstance(collection_path, str) else None,
            id_field=_required_string(records_raw, "id_field", "records"),
            page_field=_required_string(records_raw, "page_field", "records"),
            title_field=_optional_string(records_raw, "title_field", "records"),
        ),
        pages=PageConfig(
            include=_string_list(pages_raw, "include", "pages", required=True),
            exclude=_string_list(pages_raw, "exclude", "pages", required=False),
            identifier=_page_value_config(pages_raw.get("id"), "pages.id"),
            title=title_config,
        ),
        rules=_rule_config(root.get("rules")),
    )
