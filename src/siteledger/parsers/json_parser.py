from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit

from siteledger.config import RecordConfig
from siteledger.models import Record


class JsonRecordError(RuntimeError):
    """Raised when a configured JSON record source cannot be interpreted."""


CollectionToken = str | int


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


def _normalize_record_file(value: str) -> PurePosixPath:
    normalized = value.replace("\\", "/").strip()
    if not normalized or normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise JsonRecordError(f"record file must be relative to the site root: {value!r}")
    path = PurePosixPath(normalized)
    if ".." in path.parts:
        raise JsonRecordError(f"record file must not escape the site root: {value!r}")
    return path


def _collection_tokens(collection_path: str) -> tuple[CollectionToken, ...]:
    tokens: list[CollectionToken] = []
    index = 0
    length = len(collection_path)
    while index < length:
        if collection_path[index] == ".":
            raise JsonRecordError(f"empty component in collection path {collection_path!r}")

        start = index
        while index < length and collection_path[index] not in ".[":
            index += 1
        component = collection_path[start:index].strip()
        if component:
            tokens.append(int(component) if component.isdigit() else component)
        elif start == index and collection_path[index] != "[":
            raise JsonRecordError(f"empty component in collection path {collection_path!r}")

        while index < length and collection_path[index] == "[":
            end = collection_path.find("]", index + 1)
            if end == -1:
                raise JsonRecordError(f"unclosed index in collection path {collection_path!r}")
            raw_index = collection_path[index + 1 : end]
            if not raw_index.isdigit():
                raise JsonRecordError(
                    f"collection index must be a non-negative integer in {collection_path!r}"
                )
            tokens.append(int(raw_index))
            index = end + 1

        if index < length:
            if collection_path[index] != ".":
                raise JsonRecordError(f"invalid collection path {collection_path!r}")
            index += 1
            if index == length:
                raise JsonRecordError(f"empty component in collection path {collection_path!r}")

    if not tokens:
        raise JsonRecordError("collection path must not be empty")
    return tuple(tokens)


def _walk_collection(data: Any, collection_path: str | None, source: Path) -> tuple[Any, str]:
    if not collection_path:
        return data, "$"

    current = data
    json_location = "$"
    for token in _collection_tokens(collection_path):
        if isinstance(token, str):
            if not isinstance(current, dict) or token not in current:
                raise JsonRecordError(
                    f"collection path {collection_path!r} was not found in {source} "
                    f"at {json_location}"
                )
            current = current[token]
            json_location += f".{token}"
        else:
            if not isinstance(current, list) or token >= len(current):
                raise JsonRecordError(
                    f"collection path {collection_path!r} has no index {token} in {source} "
                    f"at {json_location}"
                )
            current = current[token]
            json_location += f"[{token}]"
    return current, json_location


def _read_json(source: Path, relative_path: PurePosixPath) -> Any:
    try:
        return json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise JsonRecordError(f"record file does not exist: {relative_path}") from exc
    except UnicodeDecodeError as exc:
        raise JsonRecordError(f"record file is not valid UTF-8: {relative_path}") from exc
    except OSError as exc:
        raise JsonRecordError(f"could not read record file {relative_path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise JsonRecordError(
            f"invalid JSON in {relative_path} at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def load_records(root: Path, config: RecordConfig) -> tuple[Record, ...]:
    """Load configured JSON records with stable source and field locations."""

    records: list[Record] = []
    for relative_name in config.files:
        relative_path = _normalize_record_file(relative_name)
        source = root.joinpath(*relative_path.parts)
        data = _read_json(source, relative_path)
        collection, base_location = _walk_collection(data, config.collection_path, source)
        if not isinstance(collection, list):
            raise JsonRecordError(f"configured collection in {relative_path} must be a JSON array")

        for index, item in enumerate(collection):
            location = f"{base_location}[{index}]"
            if not isinstance(item, dict):
                actual_type = type(item).__name__
                raise JsonRecordError(
                    f"record at {relative_path}:{location} must be an object, got {actual_type}"
                )

            identifier_location = f"{location}.{config.id_field}"
            page_location = f"{location}.{config.page_field}"
            identifier = item.get(config.id_field)
            page_value = item.get(config.page_field)
            if not isinstance(identifier, str) or not identifier.strip():
                raise JsonRecordError(
                    f"field {relative_path}:{identifier_location} must be a non-empty string"
                )
            if not isinstance(page_value, str) or not page_value.strip():
                raise JsonRecordError(
                    f"field {relative_path}:{page_location} must be a non-empty string"
                )

            try:
                page_path = normalize_site_path(page_value)
            except JsonRecordError as exc:
                raise JsonRecordError(f"{relative_path}:{page_location}: {exc}") from exc

            records.append(
                Record(
                    identifier=identifier.strip(),
                    page_path=page_path,
                    source_file=relative_path,
                    location=location,
                    identifier_location=identifier_location,
                    page_location=page_location,
                    source_index=index,
                )
            )

    return tuple(records)
