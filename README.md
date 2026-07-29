# SiteLedger

SiteLedger audits static websites whose HTML pages, JSON indexes, metadata, navigation, and local assets can drift out of agreement. It reports inconsistencies without modifying the source site.

The project is being built from a real integration need at TempleSophia.org while keeping all auditing behavior reusable and configuration-driven.

## Current release

Version `0.2.0` provides the first complete record/page audit plus richer parsing needed by the next rule milestones.

### Audit behavior

- Configurable JSON record files and nested collection paths
- Configurable HTML include and exclude patterns
- Recursive `**` glob support across Windows, macOS, and Linux
- Deterministic POSIX-style relative paths
- Site-root escape protection and clear scan errors
- Missing record-page detection (`SL001`)
- Orphaned HTML page detection (`SL002`)
- Record/page identifier mismatch detection (`SL003`)
- Duplicate record ID, record URL, and page ID detection (`SL006`)
- Deterministic terminal output and CI-friendly exit codes

### Parsed HTML data

Each discovered page can now preserve:

- Configured page identifier and source line
- Configured title, with `<title>` as the default
- Element IDs and legacy named anchors
- Site-local hyperlinks, including fragment-only links
- Local images, stylesheets, scripts, and explicit downloads

External URLs, `mailto:` links, and data URIs are excluded from local-reference collections. This release collects these references for later validation; it does not yet emit broken-link or missing-asset findings.

### Parsed JSON data

Each record preserves:

- Record JSON path
- Identifier field JSON path
- Page field JSON path
- Source file and source-array index
- Normalized page path with query strings and fragments removed

Collection paths support nested objects and array indexes, for example:

```yaml
collection_path: catalog.collections[0].entries
```

Numeric dot components are also accepted:

```yaml
collection_path: catalog.collections.0.entries
```

## Installation

```bash
python -m venv .venv
```

Activate the environment, then install SiteLedger and its development tools:

```bash
python -m pip install -e ".[dev]"
```

## Quick start

```bash
siteledger audit ./website --config siteledger.yml
```

The repository includes a deliberately broken example:

```bash
siteledger audit examples/broken-site --config examples/siteledger.yml
```

A clean audit exits with `0`. Audit findings exit with `1`. Configuration, parsing, or execution errors exit with `2`.

## Configuration

```yaml
records:
  files:
    - data/index.json
  collection_path: entries
  id_field: id
  page_field: url

pages:
  include:
    - Library/PGM/spells/**/*.html
  exclude:
    - Library/PGM/admin/**
  id:
    selector: meta[name="entry-id"]
    attribute: content
  title:
    selector: h1
```

The `pages.title` section is optional. When omitted, SiteLedger reads the first `<title>` element. All configured file paths and glob patterns are relative to the site directory passed to `siteledger audit`.

## Architecture

```text
src/siteledger/
    cli.py              command-line interface and exit codes
    config.py           YAML schema loading and validation
    models.py           immutable records, pages, links, and assets
    scanner.py          configured cross-platform page discovery
    auditor.py          audit orchestration
    parsers/            JSON and HTML parsing
    rules/              stable rule definitions and comparisons
    reporters/          deterministic terminal reporting
```

The implementation uses a `src/` layout so local imports during development exercise the installed package rather than accidentally importing from the repository root.

## Development

```bash
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m mypy src
```

GitHub Actions runs linting and type checking on Ubuntu and runs the test suite across Python 3.11–3.14 on both Ubuntu and Windows.

## Roadmap

The next milestones use the parsed reference data to validate record/page reconciliation in greater depth, internal links and anchors, local assets, navigation sequence, JSON reports, and HTML reports.
