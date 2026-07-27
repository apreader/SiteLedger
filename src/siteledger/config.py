from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class ConfigError(ValueError):
    """Raised when a SiteLedger configuration file is missing or invalid."""


@dataclass(frozen=True, slots=True)
class RecordConfig:
    files: tuple[str, ...]
    collection_path: str | None
    id_field: str
    page_field: str


@dataclass(frozen=True, slots=True)
class PageIdConfig:
    selector: str
    attribute: str | None


@dataclass(frozen=True, slots=True)
class PageConfig:
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    identifier: PageIdConfig


@dataclass(frozen=True, slots=True)
class SiteLedgerConfig:
    records: RecordConfig
    pages: PageConfig


def _mapping(value: Any, key: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"'{key}' must be a mapping")
    return value


def _required_string(mapping: dict[str, Any], key: str, section: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"'{section}.{key}' must be a non-empty string")
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


def load_config(path: Path) -> SiteLedgerConfig:
    """Load and validate the intentionally small Milestone 1 schema."""

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
    page_id_raw = _mapping(pages_raw.get("id"), "pages.id")

    collection_path = records_raw.get("collection_path")
    if collection_path is not None and not isinstance(collection_path, str):
        raise ConfigError("'records.collection_path' must be a string or null")

    attribute = page_id_raw.get("attribute")
    if attribute is not None and (not isinstance(attribute, str) or not attribute.strip()):
        raise ConfigError("'pages.id.attribute' must be a non-empty string or null")

    return SiteLedgerConfig(
        records=RecordConfig(
            files=_string_list(records_raw, "files", "records", required=True),
            collection_path=collection_path.strip() if isinstance(collection_path, str) else None,
            id_field=_required_string(records_raw, "id_field", "records"),
            page_field=_required_string(records_raw, "page_field", "records"),
        ),
        pages=PageConfig(
            include=_string_list(pages_raw, "include", "pages", required=True),
            exclude=_string_list(pages_raw, "exclude", "pages", required=False),
            identifier=PageIdConfig(
                selector=_required_string(page_id_raw, "selector", "pages.id"),
                attribute=attribute.strip() if isinstance(attribute, str) else None,
            ),
        ),
    )
