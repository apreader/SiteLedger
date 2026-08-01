from __future__ import annotations

from collections import Counter
from pathlib import Path, PurePosixPath

from bs4 import BeautifulSoup
from bs4.element import Tag

from siteledger.models import AssetKind, Finding, Page, Severity
from siteledger.rules.common import sort_findings
from siteledger.rules.definitions import BROKEN_INTERNAL_LINK
from siteledger.rules.references import resolve_local_reference

_HTML_SUFFIXES = frozenset({".htm", ".html", ".xhtml"})


def _page_anchor_map(pages: tuple[Page, ...]) -> dict[PurePosixPath, frozenset[str]]:
    return {page.path: frozenset(anchor.name for anchor in page.anchors) for page in pages}


def _load_anchor_names(path: Path) -> frozenset[str] | None:
    try:
        markup = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None

    soup = BeautifulSoup(markup, "html.parser")
    names: set[str] = set()
    for node in soup.find_all(True):
        if not isinstance(node, Tag):
            continue
        element_id = node.get("id")
        if isinstance(element_id, str) and element_id.strip():
            names.add(element_id.strip())
        if node.name == "a":
            anchor_name = node.get("name")
            if isinstance(anchor_name, str) and anchor_name.strip():
                names.add(anchor_name.strip())
    return frozenset(names)


def _finding(
    page: Page,
    target: str,
    location: str | None,
    message: str,
    expected: str,
    suggestion: str,
) -> Finding:
    return Finding(
        severity=Severity.ERROR,
        rule_id=BROKEN_INTERNAL_LINK.rule_id,
        message=message,
        file=page.path,
        location=location,
        expected=expected,
        actual=target,
        suggestion=suggestion,
    )


def validate_internal_links(root: Path, pages: tuple[Page, ...]) -> tuple[Finding, ...]:
    """Validate site-local hyperlinks and HTML fragment anchors."""

    findings: list[Finding] = []
    anchors_by_path = _page_anchor_map(pages)
    on_demand_anchors: dict[PurePosixPath, frozenset[str] | None] = {}

    for page in pages:
        download_references = Counter(
            (asset.target, asset.location)
            for asset in page.assets
            if asset.kind is AssetKind.DOWNLOAD
        )
        for link in page.links:
            reference_key = (link.target, link.location)
            if download_references[reference_key] > 0:
                download_references[reference_key] -= 1
                continue

            resolved = resolve_local_reference(
                root,
                page.path,
                link.target,
                directory_indexes=True,
            )
            if (
                resolved.error is not None
                or resolved.path is None
                or resolved.absolute_path is None
            ):
                findings.append(
                    _finding(
                        page,
                        link.target,
                        link.location,
                        f"internal link cannot be resolved: {resolved.error or 'invalid target'}",
                        "a local target beneath the audited site root",
                        "Correct the link so it resolves beneath the audited site root.",
                    )
                )
                continue

            if not resolved.absolute_path.is_file():
                findings.append(
                    _finding(
                        page,
                        link.target,
                        link.location,
                        "internal link points to a missing file",
                        f"an existing local file at {resolved.path}",
                        "Create the target file or correct the link path.",
                    )
                )
                continue

            if resolved.fragment is None:
                continue

            if resolved.path.suffix.lower() not in _HTML_SUFFIXES:
                findings.append(
                    _finding(
                        page,
                        link.target,
                        link.location,
                        "internal link uses a fragment on a non-HTML target",
                        f"an HTML page containing anchor #{resolved.fragment}",
                        "Point the fragment to an HTML page anchor or remove the fragment.",
                    )
                )
                continue

            anchors = anchors_by_path.get(resolved.path)
            if anchors is None:
                if resolved.path not in on_demand_anchors:
                    on_demand_anchors[resolved.path] = _load_anchor_names(resolved.absolute_path)
                anchors = on_demand_anchors[resolved.path]

            if anchors is None or resolved.fragment not in anchors:
                findings.append(
                    _finding(
                        page,
                        link.target,
                        link.location,
                        "internal link points to a missing fragment anchor",
                        f"anchor #{resolved.fragment} in {resolved.path}",
                        "Add the target anchor or correct the link fragment.",
                    )
                )

    return sort_findings(findings)
