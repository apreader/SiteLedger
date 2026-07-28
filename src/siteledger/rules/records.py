from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import PurePosixPath

from siteledger.models import Finding, Page, Record, Severity
from siteledger.rules.definitions import (
    DUPLICATE_IDENTIFIER,
    IDENTIFIER_MISMATCH,
    MISSING_RECORD_PAGE,
    ORPHANED_HTML_PAGE,
)


def _duplicate_record_findings(records: tuple[Record, ...]) -> list[Finding]:
    findings: list[Finding] = []
    by_identifier: dict[str, list[Record]] = defaultdict(list)
    by_page: dict[PurePosixPath, list[Record]] = defaultdict(list)
    for record in records:
        by_identifier[record.identifier].append(record)
        by_page[record.page_path].append(record)

    for identifier, matches in sorted(by_identifier.items()):
        if len(matches) < 2:
            continue
        first = matches[0]
        locations = ", ".join(f"{item.source_file}:{item.location}" for item in matches)
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id=DUPLICATE_IDENTIFIER.rule_id,
                message=f"record identifier {identifier!r} appears {len(matches)} times",
                file=first.source_file,
                location=first.location,
                expected="one record per identifier",
                actual=locations,
                suggestion=(
                    "Assign a unique identifier to each record or remove the duplicate record."
                ),
            )
        )

    for page_path, matches in sorted(by_page.items(), key=lambda item: str(item[0])):
        if len(matches) < 2:
            continue
        first = matches[0]
        locations = ", ".join(f"{item.source_file}:{item.location}" for item in matches)
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id=DUPLICATE_IDENTIFIER.rule_id,
                message=f"page path {str(page_path)!r} is referenced by {len(matches)} records",
                file=first.source_file,
                location=first.location,
                expected="one record per page path",
                actual=locations,
                suggestion=(
                    "Keep one canonical record for the page or point each record to a "
                    "distinct page."
                ),
            )
        )
    return findings


def _duplicate_page_id_findings(pages: tuple[Page, ...]) -> list[Finding]:
    by_identifier: dict[str, list[Page]] = defaultdict(list)
    for page in pages:
        if page.identifier is not None:
            by_identifier[page.identifier].append(page)

    findings: list[Finding] = []
    for identifier, matches in sorted(by_identifier.items()):
        if len(matches) < 2:
            continue
        first = matches[0]
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id=DUPLICATE_IDENTIFIER.rule_id,
                message=f"HTML identifier {identifier!r} appears on {len(matches)} pages",
                file=first.path,
                location=first.id_location,
                expected="one HTML page per identifier",
                actual=", ".join(str(item.path) for item in matches),
                suggestion="Give each page a unique configured identifier.",
            )
        )
    return findings


def _sort_findings(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    severity_order = {Severity.ERROR: 0, Severity.WARNING: 1, Severity.INFO: 2}
    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                severity_order[finding.severity],
                finding.rule_id,
                str(finding.file),
                finding.location or "",
                finding.message,
            ),
        )
    )


def reconcile_records_and_pages(
    records: tuple[Record, ...], pages: tuple[Page, ...]
) -> tuple[Finding, ...]:
    """Compare JSON records and HTML pages using normalized page paths."""

    findings: list[Finding] = []
    findings.extend(_duplicate_record_findings(records))
    findings.extend(_duplicate_page_id_findings(pages))

    records_by_page: dict[PurePosixPath, list[Record]] = defaultdict(list)
    pages_by_path = {page.path: page for page in pages}
    for record in records:
        records_by_page[record.page_path].append(record)

    for record in records:
        page = pages_by_path.get(record.page_path)
        if page is None:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=MISSING_RECORD_PAGE.rule_id,
                    message=f"record {record.identifier!r} points to a page that was not discovered",
                    file=record.source_file,
                    location=record.location,
                    expected=str(record.page_path),
                    actual="missing",
                    suggestion="Create the page or correct the record's configured page field.",
                )
            )
            continue
        if page.identifier != record.identifier:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=IDENTIFIER_MISMATCH.rule_id,
                    message=f"record and HTML identifiers disagree for {record.page_path}",
                    file=page.path,
                    location=page.id_location,
                    expected=record.identifier,
                    actual=page.identifier or "missing",
                    suggestion="Make the JSON record ID and configured HTML page ID identical.",
                )
            )

    for page in pages:
        if page.path not in records_by_page:
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=ORPHANED_HTML_PAGE.rule_id,
                    message="HTML page has no corresponding JSON record",
                    file=page.path,
                    location=page.id_location,
                    expected="a record referencing this page",
                    actual="no matching record",
                    suggestion=(
                        "Add a record for the page or exclude the page from this collection."
                    ),
                )
            )

    return _sort_findings(findings)
