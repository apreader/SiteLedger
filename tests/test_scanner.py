from pathlib import Path, PurePosixPath

import pytest

from siteledger.config import PageConfig, PageIdConfig
from siteledger.scanner import ScanError, discover_pages, normalize_pattern, normalize_relative_path


def _config(*, include: tuple[str, ...], exclude: tuple[str, ...] = ()) -> PageConfig:
    return PageConfig(
        include=include,
        exclude=exclude,
        identifier=PageIdConfig(selector="h1", attribute=None),
    )


def test_discover_pages_honors_include_and_exclude_patterns(tmp_path: Path) -> None:
    (tmp_path / "pages/admin").mkdir(parents=True)
    (tmp_path / "pages/one.html").write_text("<h1>One</h1>", encoding="utf-8")
    (tmp_path / "pages/admin/hidden.html").write_text("<h1>Hidden</h1>", encoding="utf-8")
    (tmp_path / "pages/readme.txt").write_text("not HTML", encoding="utf-8")

    discovered = discover_pages(
        tmp_path,
        _config(include=("pages/**/*.html",), exclude=("pages/admin/**",)),
    )

    assert discovered == (PurePosixPath("pages/one.html"),)


def test_recursive_glob_matches_direct_and_nested_files(tmp_path: Path) -> None:
    (tmp_path / "pages/nested").mkdir(parents=True)
    (tmp_path / "pages/direct.html").write_text("direct", encoding="utf-8")
    (tmp_path / "pages/nested/deep.html").write_text("deep", encoding="utf-8")

    discovered = discover_pages(tmp_path, _config(include=("pages/**/*.html",)))

    assert discovered == (
        PurePosixPath("pages/direct.html"),
        PurePosixPath("pages/nested/deep.html"),
    )


def test_discovery_deduplicates_overlapping_patterns(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages/alpha.html").write_text("alpha", encoding="utf-8")

    discovered = discover_pages(
        tmp_path,
        _config(include=("pages/*.html", "pages/**/*.html")),
    )

    assert discovered == (PurePosixPath("pages/alpha.html"),)


def test_discovery_returns_deterministic_posix_paths(tmp_path: Path) -> None:
    (tmp_path / "pages").mkdir()
    (tmp_path / "pages/zeta.html").write_text("zeta", encoding="utf-8")
    (tmp_path / "pages/alpha.html").write_text("alpha", encoding="utf-8")

    discovered = discover_pages(tmp_path, _config(include=(r"pages\*.html",)))

    assert discovered == (
        PurePosixPath("pages/alpha.html"),
        PurePosixPath("pages/zeta.html"),
    )


def test_discovery_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(ScanError, match="does not exist"):
        discover_pages(tmp_path / "missing", _config(include=("**/*.html",)))


def test_discovery_rejects_file_root(tmp_path: Path) -> None:
    root = tmp_path / "site.html"
    root.write_text("content", encoding="utf-8")

    with pytest.raises(ScanError, match="not a directory"):
        discover_pages(root, _config(include=("**/*.html",)))


@pytest.mark.parametrize("pattern", ["../outside/*.html", "/absolute/*.html", r"C:\site\*.html"])
def test_normalize_pattern_rejects_paths_outside_site_root(pattern: str) -> None:
    with pytest.raises(ScanError):
        normalize_pattern(pattern)


def test_normalize_pattern_accepts_windows_separators() -> None:
    assert normalize_pattern(r"pages\**\*.html") == "pages/**/*.html"


def test_normalize_relative_path_rejects_escape(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside.html"
    with pytest.raises(ScanError, match="escapes"):
        normalize_relative_path(outside, tmp_path)
