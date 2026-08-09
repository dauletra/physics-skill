"""One slide, and the shape tree every slide-like part is built around.

A master, a layout and a slide are the same shape in OOXML: a `p:cSld`
holding a `p:spTree`. The tree always opens with a group of its own —
`p:nvGrpSpPr` and `p:grpSpPr` — and PowerPoint will not open the file if it
is missing, even when there is nothing on the slide. So it is written once,
here, and the three parts that need it ask for it.

Ids inside a tree start at 2: the group itself is 1.
"""

from __future__ import annotations

from dataclasses import dataclass

from physics_svg.ooxml import el

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

#: The namespace declarations every slide-like root carries.
NS = {"xmlns:a": A_NS, "xmlns:r": R_NS, "xmlns:p": P_NS}


def shape_tree(shapes: str = "") -> str:
    """`p:spTree` — the group everything on a slide lives in."""
    frame = el("a:off", {"x": 0, "y": 0}) + el("a:ext", {"cx": 0, "cy": 0})
    frame += el("a:chOff", {"x": 0, "y": 0}) + el("a:chExt", {"cx": 0, "cy": 0})
    return el(
        "p:spTree",
        children=el(
            "p:nvGrpSpPr",
            children=el("p:cNvPr", {"id": 1, "name": ""})
            + el("p:cNvGrpSpPr")
            + el("p:nvPr"),
        )
        + el("p:grpSpPr", children=el("a:xfrm", children=frame))
        + shapes,
    )


def slide_xml(shapes: str = "") -> str:
    """`ppt/slides/slideN.xml`.

    `p:clrMapOvr` with `a:masterClrMapping` says «no override» — the slide
    reads colours the way the master maps them. It is not optional.
    """
    return el(
        "p:sld",
        NS,
        el("p:cSld", children=shape_tree(shapes))
        + el("p:clrMapOvr", children=el("a:masterClrMapping")),
    )


@dataclass(frozen=True)
class Slide:
    """One slide of the deck: which layout it stands on, and what fills it.

    The layout is named, not numbered: a slide kind knows it wants «the
    explanation layout», and which part number that is depends on the order
    in `layouts.py`, which is not its business.
    """

    layout: str
    shapes: str = ""

    def xml(self) -> str:
        return slide_xml(self.shapes)


def slide(shapes: str = "") -> Slide:
    """A blank slide — what a deck falls back to when it has no content
    yet, and what the package tests are built from."""
    return Slide("blank", shapes)
