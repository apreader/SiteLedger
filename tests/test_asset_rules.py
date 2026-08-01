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


def test_missing_asset_categories_and_srcset_are_reported_as_sl005(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(
        root,
        """
<link rel="stylesheet" href="../assets/missing.css">
<script src="../scripts/missing.js"></script>
<img src="../images/missing.png" srcset="../images/also-missing.png 2x" alt="">
<a href="../downloads/missing.pdf" download>Missing download</a>
""",
    )

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL005"]

    assert [finding.actual for finding in findings] == [
        "../assets/missing.css",
        "../scripts/missing.js",
        "../images/missing.png",
        "../images/also-missing.png",
        "../downloads/missing.pdf",
    ]
    assert all(finding.expected is not None for finding in findings)
    assert all(finding.suggestion is not None for finding in findings)


def test_download_reference_is_not_duplicated_as_sl004(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<a href="../downloads/missing.pdf" download>Missing</a>\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))

    assert [finding.rule_id for finding in result.findings] == ["SL005"]


def test_asset_query_strings_do_not_change_file_resolution() -> None:
    result = audit_site(FIXTURE, load_config(FIXTURE / "siteledger.yml"))

    assert all(finding.rule_id != "SL005" for finding in result.findings)


def test_asset_escape_is_reported_as_sl005(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<img src="../../outside.png" alt="Outside">\n')

    result = audit_site(root, load_config(root / "siteledger.yml"))
    findings = [finding for finding in result.findings if finding.rule_id == "SL005"]

    assert len(findings) == 1
    assert "escapes the audited site root" in findings[0].message


def test_asset_category_switch_disables_only_images(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(
        root,
        """
<img src="../images/missing.png" alt="">
<script src="../scripts/missing.js"></script>
""",
    )
    config_path = root / "siteledger.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "check_images: true",
            "check_images: false",
        ),
        encoding="utf-8",
    )

    result = audit_site(root, load_config(config_path))
    findings = [finding for finding in result.findings if finding.rule_id == "SL005"]

    assert [finding.actual for finding in findings] == ["../scripts/missing.js"]


def test_sl005_rule_switch_disables_all_asset_findings(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    _append_to_home(root, '\n<img src="../images/missing.png" alt="">\n')
    config_path = root / "siteledger.yml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8") + "\nrules:\n  SL005: false\n",
        encoding="utf-8",
    )

    result = audit_site(root, load_config(config_path))

    assert all(finding.rule_id != "SL005" for finding in result.findings)
