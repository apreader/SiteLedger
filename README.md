# SiteLedger

SiteLedger audits static websites whose HTML pages, JSON indexes, metadata, navigation, and local assets can drift out of agreement. It reports inconsistencies without modifying the source site.

The project is being built from a real integration need at TempleSophia.org while keeping all auditing behavior reusable and configuration-driven.

## Current release

Version `0.4.0` adds internal-link, fragment-anchor, and local-asset validation to the record/page reconciliation introduced in `0.3.0`.

### Audit behavior

- Configurable JSON record files and nested collection paths
- Configurable HTML include and exclude patterns
- Recursive `**` glob support across Windows, macOS, and Linux
- Deterministic POSIX-style relative paths and finding order
- Site-root escape protection and clear scan errors
- Missing record pages and orphaned HTML pages
- Missing, duplicate, and mismatched identifiers
- Missing or malformed record page paths
- Optional record/page title comparison
- Relative, root-relative, query-string, and directory-index link resolution
- Same-page and cross-page fragment-anchor validation
- URL-decoded local paths and fragment names
- Local image, stylesheet, script, and explicit-download validation
- Responsive-image checks for `img[srcset]` and `source[srcset]`
- Per-rule and per-asset-category switches
- Deterministic terminal output and CI-friendly exit codes

Structurally invalid JSON, unreadable files, and invalid configuration remain execution errors with exit code `2`. Invalid fields inside otherwise valid record objects become actionable audit findings, allowing the rest of the collection to be checked in the same run.

External URLs and non-file schemes such as `mailto:`, `tel:`, `data:`, and `javascript:` are outside local validation. SiteLedger does not make network requests during an audit.

### Rule reference

| Rule | Name | Reported condition |
| --- | --- | --- |
| `SL001` | `missing-record-page` | A valid record page path was not discovered. |
| `SL002` | `orphaned-html-page` | A discovered HTML page has no record pointing to it. |
| `SL003` | `identifier-mismatch` | A record ID and its HTML page ID disagree. |
| `SL004` | `broken-internal-link` | A local link target, directory index, or fragment anchor is missing or invalid. |
| `SL005` | `missing-local-asset` | A referenced local image, stylesheet, script, or download is missing or invalid. |
| `SL006` | `duplicate-identifier` | A record ID, page path, or HTML page ID is duplicated. |
| `SL008` | `missing-record-identifier` | A record ID field is missing, empty, or not a string. |
| `SL009` | `invalid-record-page` | A record page field is missing, empty, external, or otherwise invalid. |
| `SL010` | `missing-page-identifier` | The configured page ID selector yields no usable value. |
| `SL011` | `title-mismatch` | Configured record and page titles are missing or disagree. |

Every finding includes severity, rule ID, source file, source location when available, expected value, actual value, and a suggested corrective action.

### Link validation

SiteLedger validates local links collected from `a[href]` and `area[href]`.

Supported forms include:

```text
chapter.html
chapter.html?view=print
chapter.html#section
#section
../chapter/
/Library/PGM/index.html
```

An existing directory target resolves to its `index.html`. Fragment-only links resolve against the source page. Fragments on HTML files outside the configured page include patterns are parsed on demand so their anchors can still be validated.

Explicit download links are handled by `SL005` rather than being reported a second time as `SL004`.

### Asset validation

SiteLedger validates local references collected from:

- `img[src]`
- `img[srcset]`
- `source[srcset]`
- `link[rel~="stylesheet"][href]`
- `script[src]`
- `a[download][href]`

Query strings and fragments do not change which local file is checked. References that escape the audited site root are findings and are never followed outside that root.

### Parsed JSON data

Each record preserves:

- Record JSON path
- Identifier, page, and optional title field JSON paths
- Source file and source-array index
- Normalized page path with query strings and fragments removed
- Invalid or missing field values for reconciliation findings

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
  title_field: title

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

assets:
  check_images: true
  check_stylesheets: true
  check_scripts: true
  check_downloads: true

rules:
  SL002: false
  SL011: true
```

The `records.title_field`, `pages.title`, `assets`, and `rules` sections are optional. Every known rule and asset category is enabled by default. Switches require Boolean values, and unknown keys or rule IDs are rejected as configuration errors.

All configured file paths and glob patterns are relative to the site directory passed to `siteledger audit`.

## Architecture

```text
src/siteledger/
    cli.py              command-line interface and exit codes
    config.py           YAML schema and validation switches
    models.py           immutable records, pages, links, assets, and findings
    scanner.py          configured cross-platform page discovery
    auditor.py          audit orchestration
    parsers/            JSON and HTML parsing
    rules/
        records.py      record/page reconciliation
        links.py        local target and fragment validation
        assets.py       local asset validation
        references.py   safe local URL resolution
        common.py       deterministic finding ordering
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

GitHub Actions runs linting, formatting, and type checking on Ubuntu and runs the test suite across Python 3.11–3.14 on both Ubuntu and Windows.

## Roadmap

Milestone 6 adds structured JSON output, a browsable HTML report, severity filtering, and richer terminal summaries. Navigation-sequence validation follows using the same read-only, configuration-driven rule architecture.
