from __future__ import annotations

from collections.abc import Iterable

from siteledger.models import Finding, Severity


def sort_findings(findings: Iterable[Finding]) -> tuple[Finding, ...]:
    """Return findings in a deterministic, severity-aware order."""

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
