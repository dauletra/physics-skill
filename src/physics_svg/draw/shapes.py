"""Nodes -> DrawingML: the second serialiser of the same drawing.

The sibling of `Node.svg()`, and the reason the drawing layer keeps its
pictures as a tree of nodes instead of a string: a graph in a Word file is
a group of **native shapes** — lines, curves, text boxes — that a teacher can
move, resize and print at any scale, not a picture pasted onto the page.

Two things this module owns, both of which Word is unforgiving about:

* **No nested frames.** DrawingML knows shift, scale, rotate and flip, and
  nothing else; there is no arbitrary matrix and no group-local coordinate
  system to lean on. So a drawing arrives here already flat — see
  `Group.flattened()` — and every coordinate is absolute inside one frame.
* **Zero extent is invalid.** A horizontal line has a bounding box of zero
  height, and `a:ext cy="0"` makes Word reject the document. Lines, polylines
  and paths are therefore emitted as shapes the size of the whole picture,
  with their geometry in absolute coordinates; only shapes that cannot be
  degenerate get a box of their own.

The escape hatch is closed on purpose: `Raw` has no equivalent here and never
will. A type that needs something new gets a node, and a node gets both
serialisers — that is what keeps «one drawing, two formats» true as the
library grows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

from physics_svg.draw.geometry import BBox, Pt
from physics_svg.draw.nodes import (
    ASCENT,
    Circle,
    Ellipse,
    Group,
    Line,
    Node,
    Path,
    Polyline,
    Rect,
    Text,
    Unsupported,
)
from physics_svg.draw.pathdata import ArcTo, Close, CurveTo, LineTo, Move, arc_geometry
from physics_svg.draw.style import DASH, Style
from physics_svg.draw.text import FONT_STACK, clean, split_scripts, text_width

#: English Metric Units per CSS pixel at 96 dpi, and per point.
EMU_PER_PX = 9525
EMU_PER_PT = 12700

#: DrawingML angles are in sixtieths of a thousandth of a degree.
_ANGLE = 60000

#: SVG dash arrays we emit, as the presets Word understands.
_DASH = {DASH["dashed"]: "dash", DASH["dotted"]: "sysDot"}

#: Height of a label's box relative to its font size — ascent, descent and a
#: little slack, so Word never decides the text does not fit.
_LINE_BOX = 1.4


@dataclass(frozen=True)
class Frame:
    """The picture's box and how it maps to EMU.

    `sx` and `sy` differ only for a ruling stretched to the column width —
    the one case the on-screen page renders with a non-uniform scale.
    """

    box: BBox
    sx: float
    sy: float

    def x(self, value: float) -> int:
        return round((value - self.box.x0) * self.sx)

    def y(self, value: float) -> int:
        return round((value - self.box.y0) * self.sy)

    def point(self, p: Pt) -> tuple[int, int]:
        return self.x(p.x), self.y(p.y)

    def length(self, value: float) -> int:
        """A thickness or a radius: one number, so the two scales average."""
        return max(1, round(value * math.sqrt(self.sx * self.sy)))

    def points(self, value: float) -> float:
        """A font size in points — text in a box does not scale with the
        shape, so the size has to carry the picture's scale itself."""
        return value * self.sx / EMU_PER_PT

    @property
    def width(self) -> int:
        return max(1, round(self.box.width * self.sx))

    @property
    def height(self) -> int:
        return max(1, round(self.box.height * self.sy))


class Drawing:
    """One picture: shapes with ids unique inside it."""

    def __init__(self, frame: Frame) -> None:
        self.frame = frame
        self._ids = 0

    def _id(self) -> int:
        self._ids += 1
        return self._ids

    # --- the group ------------------------------------------------------

    def group(self, nodes: Sequence[Node]) -> str:
        """`wpg:wgp` — the whole picture as one group of shapes."""
        extent = (
            f'<a:off x="0" y="0"/><a:ext cx="{self.frame.width}" cy="{self.frame.height}"/>'
            f'<a:chOff x="0" y="0"/><a:chExt cx="{self.frame.width}" cy="{self.frame.height}"/>'
        )
        body = "".join(self.shape(node) for node in _flatten(nodes))
        return (
            "<wpg:wgp><wpg:cNvGrpSpPr/>"
            f"<wpg:grpSpPr><a:xfrm>{extent}</a:xfrm></wpg:grpSpPr>"
            f"{body}</wpg:wgp>"
        )

    # --- one node -------------------------------------------------------

    def shape(self, node: Node) -> str:
        if isinstance(node, Line):
            return self._path_shape([Move(node.a), LineTo(node.b)], node.style)
        if isinstance(node, Polyline):
            segments: list[object] = [Move(node.points[0])]
            segments.extend(LineTo(p) for p in node.points[1:])
            if node.closed:
                segments.append(Close())
            return self._path_shape(segments, node.style)
        if isinstance(node, Path):
            return self._path_shape(list(node.segments()), node.style)
        if isinstance(node, Rect):
            return self._preset_shape(node.bbox(), _rect_geometry(node), node.style)
        if isinstance(node, (Circle, Ellipse)):
            return self._preset_shape(
                node.bbox(), '<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>', node.style
            )
        if isinstance(node, Text):
            return self._text_shape(node)
        raise Unsupported(
            f"узел '{type(node).__name__}' не переводится в фигуры Word — "
            "добавь его в draw/shapes.py"
        )

    def _path_shape(self, segments: Sequence[object], style: Style) -> str:
        """A shape the size of the whole picture, geometry in absolute
        coordinates — see the module docstring on zero extent."""
        frame = self.frame
        # An open path is filled by default in DrawingML, which would blacken
        # every polyline of a graph.
        unfilled = "" if style.fill not in (None, "none") else ' fill="none"'
        commands = _commands(segments, frame)
        geometry = (
            "<a:custGeom><a:avLst/><a:gdLst/><a:ahLst/><a:cxnLst/>"
            '<a:rect l="0" t="0" r="r" b="b"/>'
            f'<a:pathLst><a:path w="{frame.width}" h="{frame.height}"{unfilled}>'
            f"{commands}</a:path></a:pathLst>"
            "</a:custGeom>"
        )
        box = (
            f'<a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{frame.width}" cy="{frame.height}"/></a:xfrm>'
        )
        return self._wrap(box + geometry + _fill(style) + _stroke(style, frame))

    def _preset_shape(self, box: BBox | None, geometry: str, style: Style) -> str:
        assert box is not None
        frame = self.frame
        x, y = frame.x(box.x0), frame.y(box.y0)
        cx = max(1, frame.x(box.x1) - x)
        cy = max(1, frame.y(box.y1) - y)
        placement = f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        return self._wrap(placement + geometry + _fill(style) + _stroke(style, frame))

    def _text_shape(self, node: Text) -> str:
        """A label as a text box.

        Placement is exact even though the width is only estimated: the box is
        anchored by the edge the label is anchored by, and the text is aligned
        to that same edge, so an error in the estimate moves the far edge of
        an invisible box and nothing else.
        """
        frame = self.frame
        width = max(text_extent(node), 1.0)
        offset = {"start": 0.0, "middle": -width / 2, "end": -width}[node.anchor]
        left = node.at.x + offset
        top = node.at.y - ASCENT * node.size
        x, y = frame.x(left), frame.y(top)
        cx = max(1, round(width * frame.sx))
        cy = max(1, round(node.size * _LINE_BOX * frame.sy))
        rotation = f' rot="{round(-node.rotate * _ANGLE)}"' if node.rotate else ""
        placement = (
            f"<a:xfrm{rotation}><a:off x=\"{x}\" y=\"{y}\"/>"
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
        )
        body = (
            '<wps:bodyPr rot="0" vert="horz" wrap="none" lIns="0" tIns="0" rIns="0" '
            'bIns="0" anchor="t" anchorCtr="0"><a:noAutofit/></wps:bodyPr>'
        )
        return (
            f'<wps:wsp><wps:cNvPr id="{self._id()}" name="Подпись"/>'
            '<wps:cNvSpPr txBox="1"/>'
            f"<wps:spPr>{placement}"
            '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln>'
            "</wps:spPr>"
            f"<wps:txbx><w:txbxContent>{_label_paragraph(node, frame)}</w:txbxContent></wps:txbx>"
            f"{body}</wps:wsp>"
        )

    def _wrap(self, properties: str) -> str:
        return (
            f'<wps:wsp><wps:cNvPr id="{self._id()}" name="Фигура"/><wps:cNvSpPr/>'
            f"<wps:spPr>{properties}</wps:spPr><wps:bodyPr/></wps:wsp>"
        )


def text_extent(node: Text) -> float:
    """Estimated width of a label in user units — the same estimate that sizes
    the picture's own box, so a label never sticks out of the frame."""
    return text_width(node.content, node.size)


# --- geometry -----------------------------------------------------------


def _flatten(nodes: Iterable[Node]) -> list[Node]:
    flat: list[Node] = []
    for node in nodes:
        if isinstance(node, Group):
            flat.extend(node.flattened())
        else:
            flat.append(node)
    return flat


def _commands(segments: Sequence[object], frame: Frame) -> str:
    parts: list[str] = []
    here = Pt(0.0, 0.0)
    for segment in segments:
        if isinstance(segment, Move):
            parts.append(f"<a:moveTo>{_pt(segment.to, frame)}</a:moveTo>")
            here = segment.to
        elif isinstance(segment, LineTo):
            parts.append(f"<a:lnTo>{_pt(segment.to, frame)}</a:lnTo>")
            here = segment.to
        elif isinstance(segment, CurveTo):
            parts.append(
                "<a:cubicBezTo>"
                f"{_pt(segment.c1, frame)}{_pt(segment.c2, frame)}{_pt(segment.to, frame)}"
                "</a:cubicBezTo>"
            )
            here = segment.to
        elif isinstance(segment, ArcTo):
            geometry = arc_geometry(here, segment)
            radius = frame.length(geometry.radius)
            parts.append(
                f'<a:arcTo wR="{radius}" hR="{radius}" '
                f'stAng="{round(geometry.start_deg * _ANGLE)}" '
                f'swAng="{round(geometry.sweep_deg * _ANGLE)}"/>'
            )
            here = segment.to
        elif isinstance(segment, Close):
            parts.append("<a:close/>")
    return "".join(parts)


def _pt(point: Pt, frame: Frame) -> str:
    x, y = frame.point(point)
    return f'<a:pt x="{x}" y="{y}"/>'


def _rect_geometry(node: Rect) -> str:
    if not node.radius:
        return '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>'
    shortest = min(node.width, node.height) or 1.0
    adjustment = round(min(0.5, node.radius / shortest) * 100000)
    return (
        '<a:prstGeom prst="roundRect"><a:avLst>'
        f'<a:gd name="adj" fmla="val {adjustment}"/>'
        "</a:avLst></a:prstGeom>"
    )


# --- style --------------------------------------------------------------


def _colour(value: str) -> str:
    """`#abc` or `#aabbcc` -> `AABBCC`."""
    text = value.lstrip("#")
    if len(text) == 3:
        text = "".join(channel * 2 for channel in text)
    if len(text) != 6:
        raise Unsupported(f"цвет '{value}' не переводится в фигуры Word")
    return text.upper()


def _fill(style: Style) -> str:
    if style.fill in (None, "none"):
        return "<a:noFill/>"
    assert style.fill is not None
    if style.fill.startswith("url("):
        raise Unsupported(
            "заливка узором должна быть развёрнута в линии до перевода в фигуры"
        )
    return f'<a:solidFill><a:srgbClr val="{_colour(style.fill)}"/></a:solidFill>'


def _stroke(style: Style, frame: Frame) -> str:
    if style.stroke is None:
        return "<a:ln><a:noFill/></a:ln>"
    width = style.width if style.width is not None else 1.0
    # A ruling stretched to the column keeps its weight: the flag says the
    # line is a fixed thickness on paper, not a scaled part of the drawing.
    thickness = round(width * EMU_PER_PX * 1.5) if style.non_scaling else frame.length(width)
    dash = ""
    if style.dash is not None:
        preset = _DASH.get(style.dash)
        if preset is None:
            raise Unsupported(f"пунктир '{style.dash}' не переводится в фигуры Word")
        dash = f'<a:prstDash val="{preset}"/>'
    cap = ' cap="rnd"' if style.cap == "round" else ""
    join = "<a:bevel/>" if style.join == "bevel" else "<a:round/>"
    return (
        f'<a:ln w="{max(1, thickness)}"{cap}>'
        f'<a:solidFill><a:srgbClr val="{_colour(style.stroke)}"/></a:solidFill>'
        f"{dash}{join}</a:ln>"
    )


# --- text ---------------------------------------------------------------

_ALIGN = {"start": "left", "middle": "center", "end": "right"}


def _label_paragraph(node: Text, frame: Frame) -> str:
    """The label itself: one paragraph, no spacing of its own, the font of the
    library rather than of the document."""
    size = max(1, round(frame.points(node.size) * 2))
    colour = _colour(node.style.fill or "#000")
    bold = "<w:b/>" if node.style.font_weight == "bold" else ""
    # Letter spacing is in user units here and in twentieths of a point
    # there: one unit is 1.5 px is 1.125 pt.
    spacing = (
        f'<w:spacing w:val="{round(node.style.letter_spacing * 22.5)}"/>'
        if node.style.letter_spacing
        else ""
    )
    font = FONT_STACK.split(",")[0]
    runs = "".join(
        f"<w:r><w:rPr>"
        f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>{bold}'
        f'<w:color w:val="{colour}"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/>'
        f"{spacing}"
        f'{_script(script)}</w:rPr><w:t xml:space="preserve">{_xml_text(chunk)}</w:t></w:r>'
        for chunk, script in split_scripts(node.content)
    )
    return (
        "<w:p><w:pPr>"
        f'<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
        f'<w:jc w:val="{_ALIGN[node.anchor]}"/>'
        f"</w:pPr>{runs}</w:p>"
    )


def _script(script: str) -> str:
    if not script:
        return ""
    return f'<w:vertAlign w:val="{"superscript" if script == "sup" else "subscript"}"/>'


def _xml_text(value: str) -> str:
    """The same gate `esc()` is for SVG: markup escaped, and what XML cannot
    hold at all dropped by the one rule both serialisers share."""
    return clean(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
