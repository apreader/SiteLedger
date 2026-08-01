from __future__ import annotations

from pathlib import Path
from urllib.parse import urlsplit

from siteledger.config import AssetConfig
from siteledger.models import AssetKind, AssetReference, Finding, Page, Severity
from siteledger.rules.common import sort_findings
from siteledger.rules.definitions import MISSING_LOCAL_ASSET
from siteledger.rules.references import resolve_local_reference


def _enabled(reference: AssetReference, config: AssetConfig) -> bool:
    return {
        AssetKind.IMAGE: config.check_images,
        AssetKind.STYLESHEET: config.check_stylesheets,
        AssetKind.SCRIPT: config.check_scripts,
        AssetKind.DOWNLOAD: config.check_downloads,
    }[reference.kind]


def validate_local_assets(
    root: Path,
    pages: tuple[Page, ...],
    config: AssetConfig,
) -> tuple[Finding, ...]:
    """Validate configured categories of site-local asset references."""

    findings: list[Finding] = []
    for page in pages:
        for asset in page.assets:
            if not _enabled(asset, config):
                continue

            try:
                raw_path = urlsplit(asset.target).path
            except ValueError:
                raw_path = ""
            resolved = resolve_local_reference(
                root,
                page.path,
                asset.target,
                directory_indexes=False,
            )

            if not raw_path:
                message = f"{asset.kind.value} reference has no file path"
                expected = "a non-empty local asset path"
            elif (
                resolved.error is not None
                or resolved.path is None
                or resolved.absolute_path is None
            ):
                message = (
                    f"{asset.kind.value} reference cannot be resolved: "
                    f"{resolved.error or 'invalid target'}"
                )
                expected = "a local asset beneath the audited site root"
            elif not resolved.absolute_path.is_file():
                message = f"referenced local {asset.kind.value} file is missing"
                expected = f"an existing local file at {resolved.path}"
            else:
                continue

            findings.append(
                Finding(
                    severity=Severity.ERROR,
                    rule_id=MISSING_LOCAL_ASSET.rule_id,
                    message=message,
                    file=page.path,
                    location=asset.location,
                    expected=expected,
                    actual=asset.target,
                    suggestion=(f"Add the {asset.kind.value} file or correct the reference path."),
                )
            )

    return sort_findings(findings)
