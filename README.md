# SiteLedger

SiteLedger audits static websites whose HTML pages, JSON indexes, and metadata can drift out of agreement. It reports inconsistencies without modifying the source site.

## 

## Current vertical slice

Version `0.1.0` supports:

* Configurable JSON record files and nested collection paths
* Configurable HTML include and exclude patterns
* CSS-selector-based page identifiers
* Missing record-page detection (`SL001`)
* Orphaned HTML page detection (`SL002`)
* Record/page identifier mismatch detection (`SL003`)
* Duplicate record ID, record URL, and page ID detection (`SL006`)
* Deterministic terminal output
* CI-friendly exit codes

SiteLedger is read-only. The audit command reports findings and leaves the audited site unchanged.

## Installation

```bash
python -m venv .venv
```

Activate the environment, then install SiteLedger and its development tools:

```bash
python -m pip install -e ".\[dev]"
```

## Quick start

```bash
siteledger audit ./website --config siteledger.yml
```

The repository includes a deliberately broken example:

```bash
siteledger audit examples/broken-site --config examples/siteledger.yml
```

A clean audit exits with `0`. Audit errors exit with `1`. Configuration, parsing, or execution errors exit with `2`.

## Minimal configuration

```yaml
records:
  files:
    - data/index.json
  collection\_path: entries
  id\_field: id
  page\_field: url

pages:
  include:
    - Library/PGM/spells/\*.html
  exclude:
    - Library/PGM/admin/\*\*
  id:
    selector: meta\[name="entry-id"]
    attribute: content
```

All configured paths are interpreted relative to the site directory passed to `siteledger audit`.

## Architecture

```text
src/siteledger/
    cli.py              command-line interface and exit codes
    config.py           YAML schema loading and validation
    models.py           immutable audit data models
    scanner.py          configured page discovery
    auditor.py          vertical-slice orchestration
    parsers/            JSON and HTML parsing
    rules/              stable rule definitions and comparisons
    reporters/          deterministic terminal reporting
```

The implementation uses a `src/` layout so local imports during development exercise the installed package rather than accidentally importing from the repository root.

## Development

```bash
pytest
ruff check .
ruff format --check .
mypy
```

## Roadmap

The next milestones add richer file discovery behavior, link and anchor validation, local asset checks, JSON and HTML reports, Temple Sophia integration fixtures, and GitHub Actions.

