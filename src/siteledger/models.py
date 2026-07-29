from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath


class Severity(StrEnum):
    """Severity assigned to an audit finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AssetKind(StrEnum):
    """Kind of local asset referenced by an HTML page."""

    IMAGE = "image"
    STYLESHEET = "stylesheet"
    SCRIPT = "script"
    DOWNLOAD = "download"


@dataclass(frozen=True, slots=True)
class Finding:
    """A single actionable inconsistency discovered by SiteLedger."""

    severity: Severity
    rule_id: str
    message: str
    file: PurePosixPath
    location: str | None = None
    expected: str | None = None
    actual: str | None = None
    suggestion: str | None = None


@dataclass(frozen=True, slots=True)
class AnchorReference:
    """An HTML ``id`` or named anchor preserved for fragment validation."""

    name: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class LinkReference:
    """A site-local hyperlink preserved exactly as written in the page."""

    target: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class AssetReference:
    """A site-local image, stylesheet, script, or download reference."""

    kind: AssetKind
    target: str
    location: str | None = None


@dataclass(frozen=True, slots=True)
class Record:
    """A normalized record loaded from a configured JSON collection."""

    identifier: str
    page_path: PurePosixPath
    source_file: PurePosixPath
    location: str
    identifier_location: str
    page_location: str
    source_index: int


@dataclass(frozen=True, slots=True)
class Page:
    """A normalized HTML page discovered beneath the audited site root."""

    path: PurePosixPath
    identifier: str | None
    id_location: str | None = None
    title: str | None = None
    title_location: str | None = None
    anchors: tuple[AnchorReference, ...] = ()
    links: tuple[LinkReference, ...] = ()
    assets: tuple[AssetReference, ...] = ()


@dataclass(frozen=True, slots=True)
class AuditResult:
    """Complete deterministic output from one audit run."""

    findings: tuple[Finding, ...]
    record_count: int
    page_count: int

    @property
    def has_errors(self) -> bool:
        return any(finding.severity is Severity.ERROR for finding in self.findings)
