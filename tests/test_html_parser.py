from pathlib import Path, PurePosixPath

import pytest

from siteledger.config import PageValueConfig
from siteledger.models import AssetKind
from siteledger.parsers.html_parser import HtmlPageError, parse_pages

FIXTURES = Path(__file__).parent / "fixtures" / "html"
ID_CONFIG = PageValueConfig(selector='meta[name="entry-id"]', attribute="content")


def test_parse_page_collects_metadata_anchors_links_and_assets() -> None:
    pages = parse_pages(FIXTURES, (PurePosixPath("reference-page.html"),), ID_CONFIG)

    page = pages[0]
    assert page.identifier == "entry-001"
    assert page.id_location == "line 4"
    assert page.title == "Document Title"
    assert page.title_location == "line 5"
    assert [(anchor.name, anchor.location) for anchor in page.anchors] == [
        ("top", "line 11"),
        ("details", "line 13"),
        ("legacy-anchor", "line 14"),
    ]
    assert [link.target for link in page.links] == [
        "other.html#part",
        "#details",
        "../downloads/guide.pdf",
    ]
    assert [(asset.kind, asset.target) for asset in page.assets] == [
        (AssetKind.STYLESHEET, "../assets/site.css"),
        (AssetKind.SCRIPT, "../assets/site.js"),
        (AssetKind.DOWNLOAD, "../downloads/guide.pdf"),
        (AssetKind.IMAGE, "../images/diagram.png"),
    ]


def test_parse_page_uses_configured_title_selector() -> None:
    title_config = PageValueConfig(selector="h1", attribute=None)

    pages = parse_pages(
        FIXTURES,
        (PurePosixPath("reference-page.html"),),
        ID_CONFIG,
        title_config,
    )

    assert pages[0].title == "Visible Heading"
    assert pages[0].title_location == "line 12"


def test_parse_page_recovers_useful_data_from_malformed_markup() -> None:
    id_config = PageValueConfig(selector="main", attribute="id")

    pages = parse_pages(FIXTURES, (PurePosixPath("malformed.html"),), id_config)

    page = pages[0]
    assert page.identifier == "content"
    assert page.title == "Recoverable document"
    assert [link.target for link in page.links] == ["next.html"]


def test_parse_page_rejects_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "bad.html").write_bytes(b"<html>\xff</html>")

    with pytest.raises(HtmlPageError, match="not valid UTF-8"):
        parse_pages(tmp_path, (PurePosixPath("bad.html"),), ID_CONFIG)


def test_parse_page_reports_invalid_selector(tmp_path: Path) -> None:
    (tmp_path / "page.html").write_text("<h1>Title</h1>", encoding="utf-8")
    invalid_config = PageValueConfig(selector="h1[", attribute=None)

    with pytest.raises(HtmlPageError, match="invalid CSS selector"):
        parse_pages(tmp_path, (PurePosixPath("page.html"),), invalid_config)
