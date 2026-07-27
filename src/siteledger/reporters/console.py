from __future__ import annotations

from collections import Counter

from siteledger.models import AuditResult, Finding, Severity


def _location(finding: Finding) -> str:
    suffix = f":{finding.location}" if finding.location else ""
    return f"{finding.file}{suffix}"


def render_console(result: AuditResult) -> str:
    """Render deterministic plain-text output suitable for terminals and CI logs."""

    lines = [
        f"Scanned {result.record_count} record(s) and {result.page_count} HTML page(s)."
    ]
    if not result.findings:
        lines.append("No findings.")
        lines.append("Summary: 0 errors, 0 warnings, 0 informational findings.")
        return "\n".join(lines)

    for finding in result.findings:
        lines.append("")
        lines.append(
            f"{finding.severity.value.upper()} {finding.rule_id} {_location(finding)}"
        )
        lines.append(f"  {finding.message}")
        if finding.expected is not None:
            lines.append(f"  Expected: {finding.expected}")
        if finding.actual is not None:
            lines.append(f"  Actual: {finding.actual}")
        if finding.suggestion is not None:
            lines.append(f"  Suggested action: {finding.suggestion}")

    counts = Counter(finding.severity for finding in result.findings)
    lines.append("")
    lines.append(
        "Summary: "
        f"{counts[Severity.ERROR]} errors, "
        f"{counts[Severity.WARNING]} warnings, "
        f"{counts[Severity.INFO]} informational findings."
    )
    return "\n".join(lines)
