#!/usr/bin/env python3
"""Render every example spec of every registered type onto one page.

Visual work needs eyes, and eyes need everything at once: a change to a
shared element shows up here as five pictures going wrong, not as one golden
file failing in isolation.

The same sheet comes out as a Word file, because the library has two
backends and only one of them can be checked in a browser. A new type is not
finished until it has been looked at in both.

    python tools/contact_sheet.py            # -> dist/contact-sheet.html
    python tools/contact_sheet.py --open     # and open it in a browser
    python tools/contact_sheet.py --docx     # -> dist/contact-sheet.docx
"""

from __future__ import annotations

import argparse
import json
import sys
import webbrowser
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from physics_svg.document import build_docx, parse_block, parse_document  # noqa: E402
from physics_svg.draw import FONT_STACK, esc  # noqa: E402
from physics_svg.visuals import build_svg, load_all, parse_visual  # noqa: E402

PAGE = """<!doctype html>
<meta charset="utf-8">
<title>physics-svg — контрольный лист</title>
<style>
  body {{ font-family: {font}; margin: 0 auto; padding: 24px; max-width: 1100px;
         color: #111; background: #fff; }}
  h1 {{ font-size: 20px; }}
  h2 {{ font-size: 16px; margin-top: 32px; border-bottom: 1px solid #ddd;
        padding-bottom: 4px; }}
  .grid {{ display: flex; flex-wrap: wrap; gap: 20px; align-items: flex-start; }}
  figure {{ margin: 0; border: 1px solid #eee; padding: 10px; border-radius: 6px; }}
  figcaption {{ font-size: 12px; color: #666; margin-top: 6px; }}
  svg {{ max-width: 100%; height: auto; display: block; }}
  .fluid {{ width: 520px; }}
</style>
<h1>Контрольный лист — {count} иллюстраций</h1>
{body}
"""


def build(destination: Path) -> Path:
    sections = []
    total = 0
    for entry in load_all().values():
        figures = []
        for spec_path in entry.specs:
            raw = json.loads(spec_path.read_text(encoding="utf-8"))
            model = parse_visual(raw, spec_path.name)
            svg = build_svg(model, scope=f"{entry.tag}-{spec_path.stem}")
            figures.append(
                f'<figure class="fluid"><div>{svg}</div>'
                f"<figcaption>{esc(spec_path.stem)}</figcaption></figure>"
            )
            total += 1
        sections.append(
            f"<h2>{esc(entry.title)} <code>{entry.tag}</code> — {len(figures)}</h2>"
            f'<div class="grid">{"".join(figures)}</div>'
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        PAGE.format(font=FONT_STACK, count=total, body="\n".join(sections)), encoding="utf-8"
    )
    return destination


def build_word(destination: Path) -> Path:
    """The same specs as a Word document, drawn as native shapes.

    Built through the real document builder rather than a shortcut: what this
    file shows is what a teacher's worksheet will show, illustration for
    illustration.
    """
    blocks = []
    for entry in load_all().values():
        blocks.append({"type": "heading", "text": f"{entry.title} ({entry.tag})", "level": 2})
        for spec_path in entry.specs:
            blocks.append({"type": "text", "body": spec_path.stem})
            blocks.append(json.loads(spec_path.read_text(encoding="utf-8")))
    document = parse_document({"title": "Контрольный лист"})
    parsed = [parse_block({**raw, "id": f"b{i}"}, f"b{i}") for i, raw in enumerate(blocks)]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(build_docx(document, parsed))
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", help="where to write (default depends on the format)")
    parser.add_argument("--docx", action="store_true", help="a Word file instead of a page")
    parser.add_argument("--open", action="store_true", help="open when done")
    args = parser.parse_args()
    if args.docx:
        path = build_word(REPO_ROOT / (args.out or "dist/contact-sheet.docx"))
    else:
        path = build(REPO_ROOT / (args.out or "dist/contact-sheet.html"))
    print(f"Wrote {path}")
    if args.open:
        webbrowser.open(path.as_uri())


if __name__ == "__main__":
    main()
