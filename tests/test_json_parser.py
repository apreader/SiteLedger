from pathlib import Path, PurePosixPath

import pytest

from siteledger.config import RecordConfig
from siteledger.parsers.json_parser import JsonRecordError, load_records, normalize_site_path

FIXTURES = Path(__file__).parent / "fixtures" / "json"


def _config(
    *,
    files: tuple[str, ...] = ("nested.json",),
    collection_path: str | None = "catalog.collections[0].entries",
) -> RecordConfig:
    return RecordConfig(
        files=files,
        collection_path=collection_path,
        id_field="id",
        page_field="url",
    )


def test_load_records_supports_nested_objects_and_array_indexes() -> None:
    records = load_records(FIXTURES, _config())

    assert [record.identifier for record in records] == ["alpha", "beta"]
    assert [record.page_path for record in records] == [
        PurePosixPath("pages/alpha.html"),
        PurePosixPath("pages/beta.html"),
    ]
    assert records[0].location == "$.catalog.collections[0].entries[0]"
    assert records[0].identifier_location == "$.catalog.collections[0].entries[0].id"
    assert records[0].page_location == "$.catalog.collections[0].entries[0].url"
    assert records[0].source_index == 0
    assert records[1].source_index == 1


def test_load_records_accepts_numeric_dot_components() -> None:
    records = load_records(
        FIXTURES,
        _config(collection_path="catalog.collections.0.entries"),
    )

    assert len(records) == 2
    assert records[0].location == "$.catalog.collections[0].entries[0]"


def test_load_records_preserves_duplicate_source_locations_across_files(tmp_path: Path) -> None:
    (tmp_path / "one.json").write_text(
        '[{"id": "same", "url": "pages/one.html"}]',
        encoding="utf-8",
    )
    (tmp_path / "two.json").write_text(
        '[{"id": "same", "url": "pages/two.html"}]',
        encoding="utf-8",
    )

    records = load_records(
        tmp_path,
        _config(files=("one.json", "two.json"), collection_path=None),
    )

    assert [(record.source_file, record.identifier_location) for record in records] == [
        (PurePosixPath("one.json"), "$[0].id"),
        (PurePosixPath("two.json"), "$[0].id"),
    ]


def test_load_records_reports_malformed_json_location() -> None:
    with pytest.raises(JsonRecordError, match=r"malformed\.json at line \d+, column \d+"):
        load_records(
            FIXTURES,
            _config(files=("malformed.json",), collection_path="entries"),
        )


def test_load_records_preserves_invalid_record_field_for_reconciliation(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text(
        '{"entries": [{"id": "alpha", "url": 42}]}',
        encoding="utf-8",
    )

    records = load_records(
        tmp_path,
        _config(files=("records.json",), collection_path="entries"),
    )

    assert records[0].page_path is None
    assert records[0].page_location == "$.entries[0].url"
    assert records[0].page_actual == "int: 42"


def test_load_records_reports_non_object_record_type(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text('{"entries": ["alpha"]}', encoding="utf-8")

    with pytest.raises(JsonRecordError, match="must be an object, got str"):
        load_records(
            tmp_path,
            _config(files=("records.json",), collection_path="entries"),
        )


def test_load_records_rejects_record_files_outside_site_root(tmp_path: Path) -> None:
    with pytest.raises(JsonRecordError, match="must not escape"):
        load_records(
            tmp_path,
            _config(files=("../outside.json",), collection_path=None),
        )


def test_normalize_site_path_rejects_external_and_parent_paths() -> None:
    with pytest.raises(JsonRecordError, match="must be local"):
        normalize_site_path("https://example.com/page.html")
    with pytest.raises(JsonRecordError, match="invalid"):
        normalize_site_path("../outside.html")


def test_load_records_preserves_optional_title_field(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text(
        '[{"id": "alpha", "url": "pages/alpha.html", "title": "Alpha Title"}]',
        encoding="utf-8",
    )
    config = RecordConfig(
        files=("records.json",),
        collection_path=None,
        id_field="id",
        page_field="url",
        title_field="title",
    )

    records = load_records(tmp_path, config)

    assert records[0].title == "Alpha Title"
    assert records[0].title_location == "$[0].title"
    assert records[0].title_actual == "'Alpha Title'"


def test_load_records_preserves_missing_identifier_for_reconciliation(tmp_path: Path) -> None:
    (tmp_path / "records.json").write_text(
        '[{"url": "pages/alpha.html"}]',
        encoding="utf-8",
    )

    records = load_records(
        tmp_path,
        _config(files=("records.json",), collection_path=None),
    )

    assert records[0].identifier is None
    assert records[0].identifier_actual == "missing"
    assert records[0].identifier_location == "$[0].id"
