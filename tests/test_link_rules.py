import shutil
from pathlib import Path

from siteledger.auditor import audit_site
from siteledger.config import load_config

FIXTURE = Path(__file__).parent / "fixtures" / "validation"


def _copy_fixture(tmp_path: Path) -> Path:
    shutil.copytree(FIXTURE, tmp_path, dirs_exist_ok=True)
    return tmp_path


def _append_to_home(root: Path, markup: str) -> None:
    path = root / "pages/index.html"
    path.write_text(path.read_text(encoding="utf-8") + markup, encoding="utf-8")


def test_valid_relative_root_directory_query_and_fragment_links_pass() -> None:
    result = audit_site(FIXTURE, load_config(FIXTURE / "siteledger.yml"))

    assert result.findings == ()


def test_missing_internal_file_is_reported_as_sl004(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="missing.html">Missing</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL004"]

    assert len(findings) == 1
    assert findings[0].file.as_posix() == "pages/index.html"
    assert findings[0].actual == "missing.html"
    assert findings[0].expected == "an existing local file at pages/missing.html"
    assert findings[0].suggestion == "Create the target file or correct the link path."


def test_missing_cross_page_fragment_is_reported_as_sl004(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="guide/index.html#absent">Absent</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL004"]

    assert len(findings) == 1
    assert findings[0].expected == "anchor #absent in pages/guide/index.html"
    assert "missing fragment anchor" in findings[0].message


def test_encoded_path_and_fragment_are_resolved(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(
        root,
        '\n<a href="guide%2Findex.html#encoded%2Danchor">Encoded path</a>\n',
    )

    result = audit_site(root, load_config(root / "siteledger.yml"))

    assert all(finding.rule_id != "SL004" for finding in result.findings)


def test_link_escape_is_reported_without_accessing_parent(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="../../outside.html">Outside</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL004"]

    assert len(findings) == 1
    assert "escapes the audited site root" in findings[0].message
    assert findings[0].actual == "../../outside.html"


def test_fragment_on_non_html_file_is_reported(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="../downloads/guide.pdf#page=1">Page</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL004"]

    assert len(findings) == 1
    assert "non-HTML target" in findings[0].message


def test_anchor_is_loaded_for_existing_html_outside_page_include(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    (root / "extras").mkdir()
    (root / "extras/target.html").write_text(
        '<html><body><h2 id="spot">Spot</h2></body></html>',
        encoding="utf-8",
    )
    _append_to_home(root, '\n<a href="../extras/target.html#spot">Spot</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))

    assert all(finding.rule_id != "SL004" for finding in result.findings)


def test_sl004_rule_switch_disables_link_findings(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="missing.html">Missing</a>\n')
    config_path = root / "siteledger.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nrules:\n  SL004: false\n",
        encoding="utf-8",
    )

    result = audit_site(root, load_config(config_path))

    assert all(finding.rule_id != "SL004" for finding in result.findings)
