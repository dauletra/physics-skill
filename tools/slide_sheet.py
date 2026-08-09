#!/usr/bin/env python3
"""Every template of every slide kind, in one presentation.

The mirror of `contact_sheet.py` for the third artefact. Design work on the
player needs eyes, and eyes need everything at once: a change to a token or
to the layout shows up here as five slides going wrong, not as one golden
file failing in isolation. `docs/slide-design.md` was written from this
sheet, and every phase of it is checked against this sheet.

The sheet is a real presentation built by the real `present`: the player
draws the slides, in a browser, as it will draw them in a classroom. A
second renderer in Python is the one thing the design forbids, so there is
nothing here to draw a *picture* of a slide with.

Before each kind the sheet inserts a `section` slide. That is not decoration:
`section` is what the player builds its stage list from, so Esc gives a jump
list by kind and a kind can be reached without paging through the rest.

While the deck backend is being built (docs/pptx.md) the sheet has a second
form: the same templates as a .pptx. Kinds that have no layout yet are
skipped and named, so the sheet grows by itself as P4 lands them.

    python tools/slide_sheet.py            # -> dist/slide-sheet.html
    python tools/slide_sheet.py --open     # and open it in a browser
    python tools/slide_sheet.py --pptx     # -> dist/slide-sheet.pptx
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from physics_svg.presentation import (  # noqa: E402
    build_data,
    build_page,
    parse_presentation,
    parse_slide,
)
from physics_svg.presentation.pptx.deck import build_deck  # noqa: E402
from physics_svg.presentation.slides import load_all  # noqa: E402


def build(destination: Path) -> tuple[Path, int, int]:
    slides: list[Any] = []
    kinds = load_all()
    total = 0
    for entry in kinds.values():
        slides.append(
            parse_slide(
                {"type": "section", "text": f"{entry.title} — {entry.tag}"},
                f"section-{entry.tag}",
            )
        )
        for template in entry.templates:
            slides.append(parse_slide(template.slide, f"{entry.tag}-{template.slug}"))
            total += 1
    page = build_page(
        build_data(parse_presentation({"title": "Контрольный лист заготовок"}), slides)
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(page, encoding="utf-8")
    return destination, len(kinds), total


def build_deck_sheet(destination: Path) -> tuple[Path, int, int, list[str]]:
    """The same sheet as a deck, with the kinds that cannot be laid out yet
    left out by name rather than silently."""
    kinds = load_all()
    ready = {tag: entry for tag, entry in kinds.items() if entry.build is not None}
    waiting = sorted(set(kinds) - set(ready))
    slides: list[Any] = []
    total = 0
    for tag, entry in ready.items():
        slides.append(
            parse_slide(
                {"type": "section", "text": f"{entry.title} — {entry.tag}"},
                f"section-{tag}",
            )
        )
        for template in entry.templates:
            slides.append(parse_slide(template.slide, f"{tag}-{template.slug}"))
            total += 1
    deck = build_deck(parse_presentation({"title": "Контрольный лист заготовок"}), slides)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(deck)
    return destination, len(ready), total, waiting


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="where to write (default dist/slide-sheet.html)")
    parser.add_argument("--open", action="store_true", help="open when done")
    parser.add_argument("--pptx", action="store_true", help="собрать колоду вместо страницы")
    args = parser.parse_args()
    if args.pptx:
        path, kinds, total, waiting = build_deck_sheet(
            REPO_ROOT / (args.out or "dist/slide-sheet.pptx")
        )
        print(f"Wrote {path} — {kinds} видов, {total} заготовок")
        if waiting:
            print(f"Без раскладки в PowerPoint пока: {', '.join(waiting)}")
        if args.open:
            webbrowser.open(path.as_uri())
        return
    path, kinds, total = build(REPO_ROOT / (args.out or "dist/slide-sheet.html"))
    print(f"Wrote {path} — {kinds} видов, {total} заготовок")
    if args.open:
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()
