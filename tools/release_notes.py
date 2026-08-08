#!/usr/bin/env python3
"""Cut the notes for one release out of CHANGELOG.md.

Release notes and the changelog are the same text — written once, for the
teacher, in the file people actually read. This only slices it.

Also checks that the tag agrees with the package version, because a release
whose archive reports a different number is worse than no release.

    python tools/release_notes.py v1.2.0        -> notes on stdout
    python tools/release_notes.py v1.2.0 -o notes.md
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from physics_svg import __version__  # noqa: E402

CHANGELOG = REPO / "CHANGELOG.md"
#: `## [1.2.0] — 2026-08-01`, `## [1.2.0]`, `## 1.2.0`
SECTION = re.compile(r"^## \[?([^\]\s]+)\]?.*$", re.M)


def notes_for(version: str) -> str:
    text = CHANGELOG.read_text(encoding="utf-8")
    headings = list(SECTION.finditer(text))
    for i, heading in enumerate(headings):
        if heading.group(1) != version:
            continue
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[heading.end() : end].strip()
        if not body:
            raise SystemExit(f"раздел {version} в CHANGELOG.md пуст")
        return body
    known = ", ".join(heading.group(1) for heading in headings)
    raise SystemExit(
        f"в CHANGELOG.md нет раздела для версии {version}; есть: {known}"
    )


def check_version(tag: str) -> str:
    version = tag.lstrip("v")
    if version != __version__:
        raise SystemExit(
            f"тег {tag} не совпадает с версией пакета {__version__} — "
            "поправь physics_svg/__init__.py или тег"
        )
    return version


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag", help="тег релиза, например v1.2.0")
    parser.add_argument("-o", "--out", help="файл вместо стандартного вывода")
    args = parser.parse_args()

    version = check_version(args.tag)
    notes = notes_for(version)
    if args.out:
        Path(args.out).write_text(notes + "\n", encoding="utf-8")
        print(f"Готово: {args.out}")
    else:
        # Straight to the byte stream: the notes are Russian and may carry a
        # symbol the console encoding has no place for (the `⤢` of the player
        # already does), and a release must not die on the terminal it was
        # printed to. The file branch above is explicit about UTF-8 for the
        # same reason.
        sys.stdout.buffer.write((notes + "\n").encode("utf-8"))


if __name__ == "__main__":
    main()
