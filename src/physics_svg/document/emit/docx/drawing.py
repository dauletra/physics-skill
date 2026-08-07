"""An illustration inside a Word document.

The shapes themselves are built by the drawing layer (`draw/shapes.py`) from
the same nodes the SVG is built from; what this module knows is the part that
is about a *document* — how a picture sits in a paragraph, how wide it may be,
and that its name has to be unique on the page.

Inline, never floating: a picture belongs to the task it was drawn for, and a
floating anchor would let it drift away from its number when the teacher edits
the text above it.
"""

from __future__ import annotations

from typing import Any

from physics_svg.document.emit.docx.wml import el
from physics_svg.visuals import build_shapes

#: Word's own namespace for a group of shapes drawn in a document.
_GROUP_URI = "http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"

#: Twips to EMU: 1 twip = 1/1440 inch, 1 EMU = 1/914400 inch.
_EMU_PER_TWIP = 635


class Ids:
    """Drawing numbers, unique in one document and the same on every build."""

    def __init__(self) -> None:
        self._used = 0

    def next(self) -> int:
        self._used += 1
        return self._used


def drawing(model: Any, *, width_twips: int, ids: Ids) -> str:
    """One illustration as a run holding a group of native shapes."""
    group, cx, cy = build_shapes(model, width_emu=width_twips * _EMU_PER_TWIP)
    number = ids.next()
    inline = (
        el("wp:extent", {"cx": cx, "cy": cy})
        + el("wp:docPr", {"id": number, "name": f"Иллюстрация {number}"})
        + el(
            "a:graphic",
            children=el("a:graphicData", {"uri": _GROUP_URI}, group),
        )
    )
    return el(
        "w:r",
        children=el(
            "w:drawing",
            children=el(
                "wp:inline",
                {"distT": 0, "distB": 0, "distL": 0, "distR": 0},
                inline,
            ),
        ),
    )
