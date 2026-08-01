from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit


@dataclass(frozen=True, slots=True)
class ResolvedReference:
    """Normalized target information for one site-local URL reference."""

    path: PurePosixPath | None
    absolute_path: Path | None
    fragment: str | None
    error: str | None = None


def _normalized_path(candidate: PurePosixPath) -> PurePosixPath:
    parts: list[str] = []
    for part in candidate.parts:
        if part in ("", ".", "/"):
            continue
        if part == "..":
            if not parts:
                raise ValueError("target escapes the audited site root")
            parts.pop()
            continue
        if "\x00" in part:
            raise ValueError("target contains a null byte")
        parts.append(part)
    return PurePosixPath(*parts)


def resolve_local_reference(
    root: Path,
    source_page: PurePosixPath,
    raw_target: str,
    *,
    directory_indexes: bool,
) -> ResolvedReference:
    """Resolve a local URL against its source page without leaving ``root``."""

    try:
        parsed = urlsplit(raw_target)
    except ValueError as exc:
        return ResolvedReference(None, None, None, f"malformed URL: {exc}")

    if parsed.scheme or parsed.netloc:
        return ResolvedReference(None, None, None, "target is not site-local")

    decoded_path = unquote(parsed.path).replace("\\", "/")
    fragment = unquote(parsed.fragment) if parsed.fragment else None

    if decoded_path.startswith("/"):
        candidate = PurePosixPath(decoded_path.lstrip("/"))
    elif decoded_path:
        candidate = source_page.parent / decoded_path
    else:
        candidate = source_page

    try:
        relative_path = _normalized_path(candidate)
    except ValueError as exc:
        return ResolvedReference(None, None, fragment, str(exc))

    normalized_root = root.resolve()
    absolute_path = normalized_root.joinpath(*relative_path.parts)
    try:
        resolved_path = absolute_path.resolve(strict=False)
    except (OSError, RuntimeError) as exc:
        return ResolvedReference(None, None, fragment, f"could not resolve target: {exc}")

    if not resolved_path.is_relative_to(normalized_root):
        return ResolvedReference(None, None, fragment, "target escapes the audited site root")

    if directory_indexes and absolute_path.is_dir():
        relative_path = relative_path / "index.html"
        absolute_path = absolute_path / "index.html"
        try:
            resolved_index = absolute_path.resolve(strict=False)
        except (OSError, RuntimeError) as exc:
            return ResolvedReference(None, None, fragment, f"could not resolve target: {exc}")
        if not resolved_index.is_relative_to(normalized_root):
            return ResolvedReference(None, None, fragment, "target escapes the audited site root")

    return ResolvedReference(relative_path, absolute_path, fragment)
