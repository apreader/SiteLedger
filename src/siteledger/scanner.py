from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

from siteledger.config import PageConfig


class ScanError(RuntimeError):
    """Raised when the configured site tree cannot be scanned."""


def _relative_posix(path: Path, root: Path) -> PurePosixPath:
    return PurePosixPath(path.relative_to(root).as_posix())


def discover_pages(root: Path, config: PageConfig) -> tuple[PurePosixPath, ...]:
    """Discover configured HTML pages beneath *root* in deterministic order."""

    if not root.exists():
        raise ScanError(f"site directory does not exist: {root}")
    if not root.is_dir():
        raise ScanError(f"site path is not a directory: {root}")

    discovered: set[PurePosixPath] = set()
    try:
        for pattern in config.include:
            for path in root.glob(pattern):
                if not path.is_file():
                    continue
                relative = _relative_posix(path, root)
                if any(fnmatch(relative.as_posix(), excluded) for excluded in config.exclude):
                    continue
                discovered.add(relative)
    except OSError as exc:
        raise ScanError(f"could not scan site directory {root}: {exc}") from exc

    return tuple(sorted(discovered, key=str))
