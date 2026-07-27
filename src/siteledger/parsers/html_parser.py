from __future__ import annotations

from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup

from siteledger.config import PageIdConfig
from siteledger.models import Page


class HtmlPageError(RuntimeError):
    """Raised when a discovered HTML page cannot be parsed."""


def parse_pages(
    root: Path,
    page_paths: tuple[PurePosixPath, ...],
    identifier_config: PageIdConfig,
) -> tuple[Page, ...]:
    """Parse configured page identifiers from discovered HTML files."""

    pages: list[Page] = []
    for relative_path in page_paths:
        source = root.joinpath(*relative_path.parts)
        try:
            markup = source.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HtmlPageError(f"HTML file is not valid UTF-8: {relative_path}") from exc
        except OSError as exc:
            raise HtmlPageError(f"could not read HTML file {relative_path}: {exc}") from exc

        soup = BeautifulSoup(markup, "html.parser")
        node = soup.select_one(identifier_config.selector)
        identifier: str | None = None
        location: str | None = None
        if node is not None:
            raw_value = (
                node.get(identifier_config.attribute)
                if identifier_config.attribute is not None
                else node.get_text(" ", strip=True)
            )
            if isinstance(raw_value, str) and raw_value.strip():
                identifier = raw_value.strip()
            source_line = getattr(node, "sourceline", None)
            if isinstance(source_line, int):
                location = f"line {source_line}"

        pages.append(Page(path=relative_path, identifier=identifier, id_location=location))

    return tuple(pages)
