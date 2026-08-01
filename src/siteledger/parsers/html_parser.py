from __future__ import annotations

from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit

from bs4 import BeautifulSoup
from bs4.element import Tag
from soupsieve import SelectorSyntaxError

from siteledger.config import PageValueConfig
from siteledger.models import (
    AnchorReference,
    AssetKind,
    AssetReference,
    LinkReference,
    Page,
)


class HtmlPageError(RuntimeError):
    """Raised when a discovered HTML page cannot be parsed."""


def _location(node: Tag) -> str | None:
    source_line = getattr(node, "sourceline", None)
    if isinstance(source_line, int):
        return f"line {source_line}"
    return None


def _string_attribute(node: Tag, attribute: str) -> str | None:
    value = node.get(attribute)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _extract_value(node: Tag | None, config: PageValueConfig) -> tuple[str | None, str | None]:
    if node is None:
        return None, None
    raw_value = (
        node.get(config.attribute)
        if config.attribute is not None
        else node.get_text(" ", strip=True)
    )
    value = raw_value.strip() if isinstance(raw_value, str) and raw_value.strip() else None
    return value, _location(node)


def _select_value(
    soup: BeautifulSoup,
    config: PageValueConfig,
    relative_path: PurePosixPath,
) -> tuple[str | None, str | None]:
    try:
        node = soup.select_one(config.selector)
    except SelectorSyntaxError as exc:
        raise HtmlPageError(
            f"invalid CSS selector {config.selector!r} while parsing {relative_path}: {exc}"
        ) from exc
    return _extract_value(node, config)


def _local_target(raw_target: str | None) -> str | None:
    if raw_target is None:
        return None
    target = raw_target.strip()
    if not target:
        return None
    try:
        parsed = urlsplit(target)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    return target


def _parse_anchors(soup: BeautifulSoup) -> tuple[AnchorReference, ...]:
    anchors: list[AnchorReference] = []
    for node in soup.find_all(True):
        if not isinstance(node, Tag):
            continue
        element_id = _string_attribute(node, "id")
        if element_id is not None:
            anchors.append(AnchorReference(name=element_id, location=_location(node)))
        if node.name == "a":
            anchor_name = _string_attribute(node, "name")
            if anchor_name is not None:
                anchors.append(AnchorReference(name=anchor_name, location=_location(node)))
    return tuple(anchors)


def _parse_links(soup: BeautifulSoup) -> tuple[LinkReference, ...]:
    links: list[LinkReference] = []
    for node in soup.find_all(("a", "area")):
        if not isinstance(node, Tag):
            continue
        target = _local_target(_string_attribute(node, "href"))
        if target is not None:
            links.append(LinkReference(target=target, location=_location(node)))
    return tuple(links)


def _append_asset(
    assets: list[AssetReference],
    node: Tag,
    kind: AssetKind,
    attribute: str,
) -> None:
    target = _local_target(_string_attribute(node, attribute))
    if target is not None:
        assets.append(AssetReference(kind=kind, target=target, location=_location(node)))


def _srcset_targets(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()

    targets: list[str] = []
    position = 0
    length = len(value)
    while position < length:
        while position < length and (value[position].isspace() or value[position] == ","):
            position += 1
        if position >= length:
            break

        start = position
        is_data_url = value[start : start + 5].lower() == "data:"
        while position < length and not value[position].isspace():
            if value[position] == "," and not is_data_url:
                break
            position += 1
        raw_target = value[start:position].rstrip(",")

        while position < length and value[position] != ",":
            position += 1
        if position < length and value[position] == ",":
            position += 1

        target = _local_target(raw_target)
        if target is not None:
            targets.append(target)

    return tuple(targets)


def _append_srcset_assets(assets: list[AssetReference], node: Tag) -> None:
    for target in _srcset_targets(_string_attribute(node, "srcset")):
        assets.append(AssetReference(kind=AssetKind.IMAGE, target=target, location=_location(node)))


def _parse_assets(soup: BeautifulSoup) -> tuple[AssetReference, ...]:
    assets: list[AssetReference] = []
    for node in soup.find_all(True):
        if not isinstance(node, Tag):
            continue
        if node.name == "img":
            _append_asset(assets, node, AssetKind.IMAGE, "src")
            _append_srcset_assets(assets, node)
        elif node.name == "source":
            _append_srcset_assets(assets, node)
        elif node.name == "script":
            _append_asset(assets, node, AssetKind.SCRIPT, "src")
        elif node.name == "link":
            rel_value = node.get("rel")
            rel_items = rel_value if isinstance(rel_value, list) else [rel_value]
            rels = {str(item).lower() for item in rel_items if item is not None}
            if "stylesheet" in rels:
                _append_asset(assets, node, AssetKind.STYLESHEET, "href")
        elif node.name == "a" and node.has_attr("download"):
            _append_asset(assets, node, AssetKind.DOWNLOAD, "href")
    return tuple(assets)


def parse_pages(
    root: Path,
    page_paths: tuple[PurePosixPath, ...],
    identifier_config: PageValueConfig,
    title_config: PageValueConfig | None = None,
) -> tuple[Page, ...]:
    """Parse configured metadata and local references from discovered HTML files."""

    pages: list[Page] = []
    default_title_config = PageValueConfig(selector="title", attribute=None)
    for relative_path in page_paths:
        source = root.joinpath(*relative_path.parts)
        try:
            markup = source.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HtmlPageError(f"HTML file is not valid UTF-8: {relative_path}") from exc
        except OSError as exc:
            raise HtmlPageError(f"could not read HTML file {relative_path}: {exc}") from exc

        soup = BeautifulSoup(markup, "html.parser")
        identifier, id_location = _select_value(soup, identifier_config, relative_path)
        title, title_location = _select_value(
            soup,
            title_config or default_title_config,
            relative_path,
        )
        pages.append(
            Page(
                path=relative_path,
                identifier=identifier,
                id_location=id_location,
                title=title,
                title_location=title_location,
                anchors=_parse_anchors(soup),
                links=_parse_links(soup),
                assets=_parse_assets(soup),
            )
        )

    return tuple(pages)
