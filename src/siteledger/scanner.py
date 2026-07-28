from __future__ import annotations

import os
import re
from pathlib import Path, PurePosixPath

from siteledger.config import PageConfig


class ScanError(RuntimeError):
    """Raised when the configured site tree cannot be scanned."""


def normalize_pattern(pattern: str) -> str:
    """Return a platform-neutral, site-relative glob pattern."""

    normalized = pattern.replace("\\", "/").strip()
    if not normalized:
        raise ScanError("file pattern must not be empty")
    if normalized.startswith("/") or re.match(r"^[A-Za-z]:/", normalized):
        raise ScanError(f"file pattern must be relative to the site root: {pattern}")

    parts = PurePosixPath(normalized).parts
    if any(part == ".." for part in parts):
        raise ScanError(f"file pattern must not escape the site root: {pattern}")

    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def normalize_relative_path(path: Path, root: Path) -> PurePosixPath:
    """Return a deterministic POSIX path relative to *root*."""

    try:
        return PurePosixPath(path.resolve().relative_to(root.resolve()).as_posix())
    except ValueError as exc:
        raise ScanError(f"discovered path escapes the site root: {path}") from exc


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a POSIX glob supporting `**` as zero or more directories."""

    index = 0
    chunks = ["^"]
    while index < len(pattern):
        char = pattern[index]
        if char == "*":
            if index + 1 < len(pattern) and pattern[index + 1] == "*":
                index += 2
                if index < len(pattern) and pattern[index] == "/":
                    chunks.append("(?:.*/)?")
                    index += 1
                else:
                    chunks.append(".*")
                continue
            chunks.append("[^/]*")
        elif char == "?":
            chunks.append("[^/]")
        elif char == "[":
            end = pattern.find("]", index + 1)
            if end == -1:
                chunks.append(r"\[")
            else:
                content = pattern[index + 1 : end]
                if content.startswith("!"):
                    content = "^" + content[1:]
                chunks.append("[" + content + "]")
                index = end
        else:
            chunks.append(re.escape(char))
        index += 1
    chunks.append("$")
    return re.compile("".join(chunks))


def _matches(path: PurePosixPath, pattern: str) -> bool:
    return bool(_glob_to_regex(normalize_pattern(pattern)).match(path.as_posix()))


def discover_pages(root: Path, config: PageConfig) -> tuple[PurePosixPath, ...]:
    """Discover configured HTML pages beneath *root* in deterministic order."""

    normalized_root = root.resolve()
    if not normalized_root.exists():
        raise ScanError(f"site directory does not exist: {normalized_root}")
    if not normalized_root.is_dir():
        raise ScanError(f"site path is not a directory: {normalized_root}")

    includes = tuple(normalize_pattern(pattern) for pattern in config.include)
    excludes = tuple(normalize_pattern(pattern) for pattern in config.exclude)
    discovered: set[PurePosixPath] = set()

    def on_walk_error(exc: OSError) -> None:
        raise ScanError(f"could not scan site directory {normalized_root}: {exc}") from exc

    try:
        for current_root, directory_names, file_names in os.walk(
            normalized_root,
            topdown=True,
            onerror=on_walk_error,
            followlinks=False,
        ):
            directory_names.sort()
            file_names.sort()
            current = Path(current_root)
            for file_name in file_names:
                candidate = current / file_name
                relative = normalize_relative_path(candidate, normalized_root)
                if not any(_matches(relative, pattern) for pattern in includes):
                    continue
                if any(_matches(relative, pattern) for pattern in excludes):
                    continue
                discovered.add(relative)
    except OSError as exc:
        raise ScanError(f"could not scan site directory {normalized_root}: {exc}") from exc

    return tuple(sorted(discovered, key=lambda path: path.as_posix()))
