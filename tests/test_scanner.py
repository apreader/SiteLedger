from pathlib import Path, PurePosixPath

from siteledger.config import PageConfig, PageIdConfig
from siteledger.scanner import discover_pages


def test_discover_pages_honors_include_and_exclude_patterns(tmp_path: Path) -> None:
    (tmp_path / "pages/admin").mkdir(parents=True)
    (tmp_path / "pages/one.html").write_text("<h1>One</h1>", encoding="utf-8")
    (tmp_path / "pages/admin/hidden.html").write_text("<h1>Hidden</h1>", encoding="utf-8")
    (tmp_path / "pages/readme.txt").write_text("not HTML", encoding="utf-8")
    config = PageConfig(
        include=("pages/**/*.html",),
        exclude=("pages/admin/**",),
        identifier=PageIdConfig(selector="h1", attribute=None),
    )

    discovered = discover_pages(tmp_path, config)

    assert discovered == (PurePosixPath("pages/one.html"),)
