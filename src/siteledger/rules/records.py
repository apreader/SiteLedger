from __future__ import annotations

from collections import defaultdict
from pathlib import PurePosixPath

from siteledger.config import RuleConfig
from siteledger.models import Finding, Page, Record, Severity
from siteledger.rules.common import sort_findings
from siteledger.rules.definitions import (
    DUPLICATE_IDENTIFIER,
    IDENTIFIER_MISMATCH,
    INVALID_RECORD_PAGE,
    MISSING_PAGE_IDENTIFIER,
    MISSING_RECORD_IDENTIFIER,
    MISSING_RECORD_PAGE,
    ORPHANED_HTML_PAGE,
    RULES,
    TITLE_MISMATCH,
)


def _default_rule_config() -> RuleConfig:
    return RuleConfig(enabled=frozenset(RULES))


def _duplicate_record_findings(records: tuple[Record, ...]) -> list[Finding]:
    findings: list[Finding] = []
    by_identifier: dict[str, list[Record]] = defaultdict(list)
    by_page: dict[PurePosixPath, list[Record]] = defaultdict(list)
    for record in records:
        if record.identifier is not None:
            by_identifier[record.identifier].append(record)
        if record.page_path is not None:
            by_page[record.page_path].append(record)

    for identifier, matches in sorted(by_identifier.items()):
        if len(matches) < 2:
            continue
        first = matches[0]
        locations = ", ".join(f"{item.source_file}:{item.identifier_location}" for item in matches)
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id=DUPLICATE_IDENTIFIER.rule_id,
                message=f"record identifier {identifier!r} appears {len(matches)} times",
                file=first.source_file,
                location=first.identifier_location,
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
        locations = ", ".join(f"{item.source_file}:{item.page_location}" for item in matches)
        findings.append(
            Finding(
                severity=Severity.ERROR,
                rule_id=DUPLICATE_IDENTIFIER.rule_id,
                message=f"page path {str(page_path)!r} is referenced by {len(matches)} records",
                file=first.source_file,
                location=first.page_location,
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


def _record_field_findings(records: tuple[Record, ...], rules: RuleConfig) -> list[Finding]:
    findings: list[Finding] = []
    for record in records:
        if record.identifier is None and rules.is_enabled(MISSING_RECORD_IDENTIFIER.rule_id):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=MISSING_RECORD_IDENTIFIER.rule_id,
                    message="JSON record has no usable configured identifier",
                    file=record.source_file,
                    location=record.identifier_location,
                    expected="a non-empty string identifier",
                    actual=record.identifier_actual,
                    suggestion="Set the configured identifier field to a unique non-empty string.",
                )
            )
        if record.page_path is None and rules.is_enabled(INVALID_RECORD_PAGE.rule_id):
            message = "JSON record has no usable configured page path"
            if record.page_error is not None:
                message = f"JSON record page path is invalid: {record.page_error}"
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=INVALID_RECORD_PAGE.rule_id,
                    message=message,
                    file=record.source_file,
                    location=record.page_location,
                    expected="a non-empty local page path beneath the site root",
                    actual=record.page_actual,
                    suggestion="Set the configured page field to a valid site-local HTML path.",
                )
            )
    return findings


def _missing_page_identifier_findings(pages: tuple[Page, ...], rules: RuleConfig) -> list[Finding]:
    if not rules.is_enabled(MISSING_PAGE_IDENTIFIER.rule_id):
        return []
    return [
        Finding(
            severity=Severity.ERROR,
            rule_id=MISSING_PAGE_IDENTIFIER.rule_id,
            message="HTML page has no configured identifier",
            file=page.path,
            location=page.id_location,
            expected="a non-empty value selected by pages.id",
            actual="missing",
            suggestion="Add the configured page identifier or correct the pages.id selector.",
        )
        for page in pages
        if page.identifier is None
    ]


def _title_finding(record: Record, page: Page) -> Finding | None:
    if record.title_actual is None:
        return None
    if record.title is None:
        return Finding(
            severity=Severity.ERROR,
            rule_id=TITLE_MISMATCH.rule_id,
            message="JSON record has no usable configured title",
            file=record.source_file,
            location=record.title_location,
            expected="a non-empty record title",
            actual=record.title_actual,
            suggestion="Set the configured title field to the title shown on the HTML page.",
        )
    if page.title == record.title:
        return None
    return Finding(
        severity=Severity.ERROR,
        rule_id=TITLE_MISMATCH.rule_id,
        message=f"record and HTML titles disagree for {record.page_path}",
        file=page.path,
        location=page.title_location,
        expected=record.title,
        actual=page.title or "missing",
        suggestion="Make the JSON record title and configured HTML page title identical.",
    )


def reconcile_records_and_pages(
    records: tuple[Record, ...],
    pages: tuple[Page, ...],
    rules: RuleConfig | None = None,
) -> tuple[Finding, ...]:
    """Compare JSON records and HTML pages using normalized page paths."""

    configured_rules = rules or _default_rule_config()
    findings: list[Finding] = []
    findings.extend(_record_field_findings(records, configured_rules))
    findings.extend(_missing_page_identifier_findings(pages, configured_rules))
    if configured_rules.is_enabled(DUPLICATE_IDENTIFIER.rule_id):
        findings.extend(_duplicate_record_findings(records))
        findings.extend(_duplicate_page_id_findings(pages))

    records_by_page: dict[PurePosixPath, list[Record]] = defaultdict(list)
    pages_by_path = {page.path: page for page in pages}
    for record in records:
        if record.page_path is not None:
            records_by_page[record.page_path].append(record)

    for record in records:
        if record.page_path is None:
            continue
        page = pages_by_path.get(record.page_path)
        if page is None:
            if configured_rules.is_enabled(MISSING_RECORD_PAGE.rule_id):
                identifier = record.identifier or "<missing identifier>"
                message = f"record {identifier!r} points to a page that was not discovered"
                findings.append(
                    Finding(
                        severity=Severity.ERROR,
                        rule_id=MISSING_RECORD_PAGE.rule_id,
                        message=message,
                        file=record.source_file,
                        location=record.page_location,
                        expected=str(record.page_path),
                        actual="missing",
                        suggestion=(
                            "Create the page or correct the record's configured page field."
                        ),
                    )
                )
            continue

        if (
            configured_rules.is_enabled(IDENTIFIER_MISMATCH.rule_id)
            and record.identifier is not None
            and page.identifier is not None
            and page.identifier != record.identifier
        ):
            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=IDENTIFIER_MISMATCH.rule_id,
                    message=f"record and HTML identifiers disagree for {record.page_path}",
                    file=page.path,
                    location=page.id_location,
                    expected=record.identifier,
                    actual=page.identifier,
                    suggestion="Make the JSON record ID and configured HTML page ID identical.",
                )
            )

        if configured_rules.is_enabled(TITLE_MISMATCH.rule_id):
            title_finding = _title_finding(record, page)
            if title_finding is not None:
                findings.append(title_finding)

    if configured_rules.is_enabled(ORPHANED_HTML_PAGE.rule_id):
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

    return sort_findings(findings)
