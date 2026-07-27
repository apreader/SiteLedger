from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from siteledger.auditor import audit_site
from siteledger.config import ConfigError, load_config
from siteledger.parsers.html_parser import HtmlPageError
from siteledger.parsers.json_parser import JsonRecordError
from siteledger.reporters.console import render_console
from siteledger.scanner import ScanError

app = typer.Typer(
    name="siteledger",
    help="Audit consistency across static-site pages and structured indexes.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """SiteLedger command group."""


@app.command()
def audit(
    site_directory: Annotated[
        Path,
        typer.Argument(help="Root directory of the static website to audit."),
    ],
    config: Annotated[
        Path,
        typer.Option("--config", "-c", help="Path to the SiteLedger YAML configuration."),
    ],
) -> None:
    """Audit configured JSON records against configured HTML pages."""

    try:
        loaded_config = load_config(config)
        result = audit_site(site_directory, loaded_config)
    except (ConfigError, ScanError, JsonRecordError, HtmlPageError) as exc:
        typer.echo(f"SiteLedger error: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    typer.echo(render_console(result))
    raise typer.Exit(code=1 if result.has_errors else 0)
