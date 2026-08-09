#!/usr/bin/env python3
"""Every template of every slide kind, in one deck.

The mirror of `contact_sheet.py` for the third artefact. Design work on the
slides needs eyes, and eyes need everything at once: a change to a token or
to a layout shows up here as five slides going wrong, not as one golden file
failing in isolation. `docs/slide-design.md` was written from this sheet, and
every phase of `docs/pptx.md` is checked against it.

The sheet is a real deck built by the real `build_deck`, opened in real
PowerPoint — there is nothing here that draws a *picture* of a slide, because
a second renderer is the one thing the design forbids.

Before each kind the sheet inserts a `section` slide. That is not decoration:
it is what makes the kinds findable in the slide sorter, and a kind can be
reached without paging through the rest.

    python tools/slide_sheet.py            # -> dist/slide-sheet.pptx
    python tools/slide_sheet.py --open     # and open it in PowerPoint
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import webbrowser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from physics_svg.presentation import parse_presentation, parse_slide  # noqa: E402
from physics_svg.presentation.pptx.deck import build_deck  # noqa: E402
from physics_svg.presentation.slides import load_all  # noqa: E402


def build(destination: Path) -> tuple[Path, int, int]:
    kinds = load_all()
    slides: list[Any] = []
    total = 0
    for tag, entry in kinds.items():
        slides.append(
            parse_slide(
                {"type": "section", "text": f"{entry.title} — {entry.tag}"},
                f"section-{tag}",
            )
        )
        for template in entry.templates:
            slides.append(parse_slide(template.slide, f"{tag}-{template.slug}"))
            total += 1
    deck, notes = build_deck(parse_presentation({"title": "Контрольный лист заготовок"}), slides)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(deck)
    for note in notes:
        print(f"  {note}")
    return destination, len(kinds), total


def show(path: Path) -> None:
    """Hand the file to whatever opens a .pptx here.

    `webbrowser` would offer to download it; on Windows the shell knows what
    a deck is, and everywhere else `xdg-open`/`open` does.
    """
    opener = {"win32": ("cmd", "/c", "start", ""), "darwin": ("open",)}.get(
        sys.platform, ("xdg-open",)
    )
    try:
        subprocess.run([*opener, str(path)], check=False)
    except OSError:  # pragma: no cover - no desktop to hand it to
        webbrowser.open(path.as_uri())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="where to write (default dist/slide-sheet.pptx)")
    parser.add_argument("--open", action="store_true", help="open when done")
    args = parser.parse_args()
    path, kinds, total = build(REPO_ROOT / (args.out or "dist/slide-sheet.pptx"))
    print(f"Wrote {path} — {kinds} видов, {total} заготовок")
    if args.open:
        show(path)


if __name__ == "__main__":
    main()
