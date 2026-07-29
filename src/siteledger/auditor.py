from __future__ import annotations

from pathlib import Path

from siteledger.config import SiteLedgerConfig
from siteledger.models import AuditResult
from siteledger.parsers.html_parser import parse_pages
from siteledger.parsers.json_parser import load_records
from siteledger.rules.records import reconcile_records_and_pages
from siteledger.scanner import discover_pages


def audit_site(root: Path, config: SiteLedgerConfig) -> AuditResult:
    """Run the configured record/page audit against a local site."""

    normalized_root = root.resolve()
    page_paths = discover_pages(normalized_root, config.pages)
    records = load_records(normalized_root, config.records)
    pages = parse_pages(
        normalized_root,
        page_paths,
        config.pages.identifier,
        config.pages.title,
    )
    findings = reconcile_records_and_pages(records, pages)
    return AuditResult(
        findings=findings,
        record_count=len(records),
        page_count=len(pages),
    )
