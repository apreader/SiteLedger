from __future__ import annotations

import json
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from siteledger.config import RecordConfig
from siteledger.models import Record


class JsonRecordError(RuntimeError):
    """Raised when a configured JSON record source cannot be interpreted."""


def normalize_site_path(value: str) -> PurePosixPath:
    """Normalize a site-local URL or path into a root-relative POSIX path."""

    parsed = urlsplit(value.strip())
    if parsed.scheme or parsed.netloc:
        raise JsonRecordError(f"record page path must be local, got: {value!r}")
    normalized = unquote(parsed.path).replace("\\", "/").lstrip("/")
    path = PurePosixPath(normalized)
    if not normalized or ".." in path.parts:
        raise JsonRecordError(f"record page path is invalid: {value!r}")
    return path


def _walk_collection(data: Any, collection_path: str | None, source: Path) -> tuple[Any, str]:
    if not collection_path:
        return data, "$"

    current = data
    json_location = "$"
    for component in collection_path.split("."):
        if not component:
            raise JsonRecordError(f"empty component in collection path for {source}")
        if not isinstance(current, dict) or component not in current:
            raise JsonRecordError(f"collection path {collection_path!r} was not found in {source}")
        current = current[component]
        json_location += f".{component}"
    return current, json_location


def load_records(root: Path, config: RecordConfig) -> tuple[Record, ...]:
    """Load all configured JSON records and preserve JSON locations."""

    records: list[Record] = []
    for relative_name in config.files:
        relative_path = PurePosixPath(relative_name.replace("\\", "/").lstrip("/"))
        source = root.joinpath(*relative_path.parts)
        try:
            data = json.loads(source.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise JsonRecordError(f"record file does not exist: {relative_path}") from exc
        except OSError as exc:
            raise JsonRecordError(f"could not read record file {relative_path}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise JsonRecordError(
                f"invalid JSON in {relative_path} at line {exc.lineno}, "
                f"column {exc.colno}: {exc.msg}"
            ) from exc

        collection, base_location = _walk_collection(data, config.collection_path, source)
        if not isinstance(collection, list):
            raise JsonRecordError(f"configured collection in {relative_path} must be a JSON array")

        for index, item in enumerate(collection):
            location = f"{base_location}[{index}]"
            if not isinstance(item, dict):
                raise JsonRecordError(f"record at {relative_path}:{location} must be an object")
            identifier = item.get(config.id_field)
            page_value = item.get(config.page_field)
            if not isinstance(identifier, str) or not identifier.strip():
                raise JsonRecordError(
                    f"record at {relative_path}:{location} has no valid {config.id_field!r}"
                )
            if not isinstance(page_value, str) or not page_value.strip():
                raise JsonRecordError(
                    f"record at {relative_path}:{location} has no valid {config.page_field!r}"
                )
            records.append(
                Record(
                    identifier=identifier.strip(),
                    page_path=normalize_site_path(page_value),
                    source_file=relative_path,
                    location=location,
                )
            )

    return tuple(records)
