from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    """Stable public identity and summary for one SiteLedger rule."""

    rule_id: str
    slug: str
    summary: str


MISSING_RECORD_PAGE = RuleDefinition(
    "SL001", "missing-record-page", "JSON record points to a missing page"
)
ORPHANED_HTML_PAGE = RuleDefinition("SL002", "orphaned-html-page", "HTML page has no JSON record")
IDENTIFIER_MISMATCH = RuleDefinition(
    "SL003", "identifier-mismatch", "Record and page identifiers disagree"
)
DUPLICATE_IDENTIFIER = RuleDefinition(
    "SL006", "duplicate-identifier", "Identifier or URL is duplicated"
)

RULES: dict[str, RuleDefinition] = {
    rule.rule_id: rule
    for rule in (
        MISSING_RECORD_PAGE,
        ORPHANED_HTML_PAGE,
        IDENTIFIER_MISMATCH,
        DUPLICATE_IDENTIFIER,
    )
}
