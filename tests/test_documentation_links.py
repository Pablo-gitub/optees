from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
IGNORED_PREFIXES = ("http://", "https://", "mailto:", "data:")


def _markdown_files() -> list[Path]:
    ignored_directories = {".git", ".pytest_cache", "node_modules"}
    return sorted(
        path
        for path in REPOSITORY_ROOT.rglob("*.md")
        if not ignored_directories.intersection(path.relative_to(REPOSITORY_ROOT).parts)
    )


def _local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        target = target[1 : target.index(">")]
    else:
        target = target.split(maxsplit=1)[0]
    if not target or target.startswith(("#", *IGNORED_PREFIXES)):
        return None
    return unquote(target.split("#", 1)[0])


def test_local_markdown_links_resolve() -> None:
    broken: list[str] = []
    for document in _markdown_files():
        for match in MARKDOWN_LINK.finditer(document.read_text(encoding="utf-8")):
            target = _local_target(match.group(1))
            if target is None:
                continue
            resolved = (document.parent / target).resolve()
            if not resolved.exists():
                source = document.relative_to(REPOSITORY_ROOT)
                broken.append(f"{source}: {target}")

    assert not broken, "Broken local Markdown links:\n" + "\n".join(broken)
