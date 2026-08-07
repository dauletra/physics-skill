"""Drawing primitives: a small tree of immutable nodes that knows both how to
serialise itself to SVG and how much room it takes.

Two things every node must provide:

* `svg()` — markup, with all numbers formatted through `num()` so output is
  byte-stable across runs and platforms (golden tests depend on it);
* `bbox()` — extent in local coordinates, which is what lets a canvas compute
  its own `viewBox` instead of every generator hard-coding one. A node that
  returns `None` contributes nothing to the extent.

Author text never reaches markup unescaped: `Text` escapes what it is given,
so a generator cannot forget to. Nodes that intentionally carry pre-built
markup exist (`Raw`), and they are the only place where that responsibility
moves to the caller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Sequence

from physics_svg.draw.geometry import IDENTITY, BBox, Pt, Transform, polar, union_all
from physics_svg.draw.pathdata import ArcTo, Close, CurveTo, LineTo, Move, Segment, sample_arc, to_d
from physics_svg.draw.pathdata import parse as parse_path
from physics_svg.draw.style import LINE, Style
from physics_svg.draw.text import num, svg_text, text_width

#: Vertical metrics of the label font as fractions of the font size, used to
#: estimate text extent (see text.text_width for the horizontal counterpart)
#: and, in the shapes backend, to put a baseline where a text box wants a top.
ASCENT = 0.78
DESCENT = 0.22

#: Arc bounding boxes are sampled rather than solved: five degrees is well
#: below the precision anything downstream needs, and it never mis-handles an
#: arc that crosses an axis.
_ARC_SAMPLE_DEG = 5.0


class Unsupported(ValueError):
    """A node cannot do what is being asked of it in this output format.

    Raised rather than approximated: a picture that comes out subtly wrong on
    a printed sheet is worse than a build that stops and says which node and
    why.
    """


class Node:
    """Base class. Subclasses are frozen dataclasses.

    Three things every node provides: `svg()`, `bbox()` and `transformed()`.
    The third is what lets a backend without nested coordinate systems — Word
    has none — flatten a drawing into plain geometry, and what lets a ruling
    tile be repeated across a field.
    """

    def svg(self) -> str:
        raise NotImplementedError

    def bbox(self) -> BBox | None:
        raise NotImplementedError

    def transformed(self, t: Transform) -> "Node":
        """The same drawing in another frame of reference."""
        raise NotImplementedError


@dataclass(frozen=True)
class Line(Node):
    a: Pt
    b: Pt
    style: Style = LINE

    def svg(self) -> str:
        return (
            f'<line x1="{num(self.a.x)}" y1="{num(self.a.y)}" '
            f'x2="{num(self.b.x)}" y2="{num(self.b.y)}"{self.style.attrs()}/>'
        )

    def bbox(self) -> BBox | None:
        return BBox.of((self.a, self.b))

    def transformed(self, t: Transform) -> "Line":
        return Line(t.apply(self.a), t.apply(self.b), _scaled(self.style, t))


@dataclass(frozen=True)
class Polyline(Node):
    points: tuple[Pt, ...]
    style: Style = LINE
    closed: bool = False

    def svg(self) -> str:
        pts = " ".join(f"{num(p.x)},{num(p.y)}" for p in self.points)
        tag = "polygon" if self.closed else "polyline"
        return f'<{tag} points="{pts}"{self.style.attrs()}/>'

    def bbox(self) -> BBox | None:
        return BBox.of(self.points)

    def transformed(self, t: Transform) -> "Polyline":
        return Polyline(
            tuple(t.apply(p) for p in self.points), _scaled(self.style, t), self.closed
        )


@dataclass(frozen=True)
class Rect(Node):
    at: Pt
    width: float
    height: float
    style: Style = LINE
    radius: float | None = None

    def svg(self) -> str:
        rx = f' rx="{num(self.radius)}"' if self.radius else ""
        return (
            f'<rect x="{num(self.at.x)}" y="{num(self.at.y)}" '
            f'width="{num(self.width)}" height="{num(self.height)}"{rx}{self.style.attrs()}/>'
        )

    def bbox(self) -> BBox | None:
        return BBox(self.at.x, self.at.y, self.at.x + self.width, self.at.y + self.height)

    def transformed(self, t: Transform) -> "Node":
        if not t.is_axis_aligned:
            # Turned, a rectangle is no longer a rectangle — its corners are.
            # Rounding does not survive that, so it is refused rather than
            # quietly dropped.
            if self.radius:
                raise Unsupported("скруглённый прямоугольник нельзя повернуть")
            box = self.bbox()
            assert box is not None
            return Polyline(tuple(t.apply(p) for p in box.corners), _scaled(self.style, t), True)
        corner = t.apply(self.at)
        far = t.apply(self.at.shifted(self.width, self.height))
        radius = None if self.radius is None else self.radius * t.scale_factor
        return Rect(
            Pt(min(corner.x, far.x), min(corner.y, far.y)),
            abs(far.x - corner.x),
            abs(far.y - corner.y),
            _scaled(self.style, t),
            radius,
        )


@dataclass(frozen=True)
class Circle(Node):
    center: Pt
    radius: float
    style: Style = LINE

    def svg(self) -> str:
        return (
            f'<circle cx="{num(self.center.x)}" cy="{num(self.center.y)}" '
            f'r="{num(self.radius)}"{self.style.attrs()}/>'
        )

    def bbox(self) -> BBox | None:
        r = self.radius
        return BBox(self.center.x - r, self.center.y - r, self.center.x + r, self.center.y + r)

    def transformed(self, t: Transform) -> "Node":
        if t.is_conformal:
            return Circle(t.apply(self.center), self.radius * t.scale_factor, _scaled(self.style, t))
        if t.is_axis_aligned:
            return Ellipse(
                t.apply(self.center),
                self.radius * abs(t.a),
                self.radius * abs(t.d),
                _scaled(self.style, t),
            )
        raise Unsupported("окружность под таким преобразованием перестаёт быть эллипсом")


@dataclass(frozen=True)
class Ellipse(Node):
    center: Pt
    rx: float
    ry: float
    style: Style = LINE

    def svg(self) -> str:
        return (
            f'<ellipse cx="{num(self.center.x)}" cy="{num(self.center.y)}" '
            f'rx="{num(self.rx)}" ry="{num(self.ry)}"{self.style.attrs()}/>'
        )

    def bbox(self) -> BBox | None:
        c = self.center
        return BBox(c.x - self.rx, c.y - self.ry, c.x + self.rx, c.y + self.ry)

    def transformed(self, t: Transform) -> "Ellipse":
        if not t.is_axis_aligned:
            raise Unsupported("эллипс нельзя повернуть: осям неоткуда взяться")
        return Ellipse(
            t.apply(self.center),
            self.rx * abs(t.a),
            self.ry * abs(t.d),
            _scaled(self.style, t),
        )


@dataclass(frozen=True)
class Path(Node):
    """An arbitrary path. `extent_points` are the points the path is known to
    pass through — `PathBuilder` fills them in, which is how a path made of
    curves still reports a usable bbox."""

    d: str
    style: Style = LINE
    extent_points: tuple[Pt, ...] = ()

    def svg(self) -> str:
        return f'<path d="{self.d}"{self.style.attrs()}/>'

    def bbox(self) -> BBox | None:
        return BBox.of(self.extent_points)

    def segments(self) -> tuple[Segment, ...]:
        """The path as structure — what a second backend and any transform
        need, and what a `d` string cannot give."""
        return parse_path(self.d)

    def transformed(self, t: Transform) -> "Path":
        """Under anything but a shift an arc stops being circular, so arcs are
        sampled — the same points the shapes backend would draw anyway."""
        moved = _move_segments(self.segments(), t)
        return Path(
            to_d(moved),
            _scaled(self.style, t),
            tuple(t.apply(p) for p in self.extent_points),
        )


@dataclass(frozen=True)
class Text(Node):
    """A label. `content` is raw author text and is escaped here."""

    at: Pt
    content: str
    size: float = 7.0
    anchor: str = "middle"  # start | middle | end
    style: Style = Style(fill="#000")
    #: Rotation in textbook degrees about `at` (used for vertical axis labels).
    rotate: float = 0.0

    def svg(self) -> str:
        anchor = f' text-anchor="{self.anchor}"' if self.anchor != "start" else ""
        transform = (
            f' transform="rotate({num(-self.rotate)} {num(self.at.x)} {num(self.at.y)})"'
            if self.rotate
            else ""
        )
        style = self.style.with_(font_size=self.size)
        return (
            f'<text x="{num(self.at.x)}" y="{num(self.at.y)}"'
            f"{anchor}{style.attrs()}{transform}>{svg_text(self.content, self.size)}</text>"
        )

    def bbox(self) -> BBox | None:
        width = text_width(self.content, self.size)
        offset = {"middle": -width / 2, "end": -width, "start": 0.0}[self.anchor]
        x0 = self.at.x + offset
        box = BBox(x0, self.at.y - ASCENT * self.size, x0 + width, self.at.y + DESCENT * self.size)
        if not self.rotate:
            return box
        return Transform.rotate(self.rotate, about=self.at).apply_box(box)

    def transformed(self, t: Transform) -> "Text":
        if not t.is_conformal:
            raise Unsupported("подпись нельзя растянуть по одной оси")
        # The turn the transform adds, in textbook degrees: the matrix turns
        # clockwise on screen, a label counts counter-clockwise.
        turn = math.degrees(math.atan2(-t.b, t.a))
        return Text(
            t.apply(self.at),
            self.content,
            self.size * t.scale_factor,
            self.anchor,
            self.style,
            self.rotate + turn,
        )


@dataclass(frozen=True)
class Group(Node):
    """Children in a local coordinate frame. This is how elements are placed
    by anchor instead of by recomputed absolute coordinates."""

    children: tuple[Node, ...]
    transform: Transform = IDENTITY
    #: Attributes inherited by children (font size, a shared stroke).
    style: Style = Style()

    def svg(self) -> str:
        attrs = self.style.attrs()
        if not self.transform.is_identity:
            t = self.transform
            values = " ".join(num(v) for v in (t.a, t.b, t.c, t.d, t.e, t.f))
            attrs += f' transform="matrix({values})"'
        inner = "".join(child.svg() for child in self.children)
        return f"<g{attrs}>{inner}</g>"

    def bbox(self) -> BBox | None:
        return self.transform.apply_box(union_all(child.bbox() for child in self.children))

    def transformed(self, t: Transform) -> "Group":
        return Group(self.children, self.transform.then(t), self.style)

    def flattened(self, t: Transform = IDENTITY) -> list[Node]:
        """Children in absolute coordinates, groups gone.

        DrawingML has no arbitrary matrix — only shift, scale, rotate and
        flip — so a backend of native shapes cannot carry a nested frame.
        Applying the matrix to the geometry removes the question instead of
        approximating it.
        """
        inner = self.transform.then(t)
        flat: list[Node] = []
        for child in self.children:
            moved = child.transformed(inner)
            if isinstance(moved, Group):
                flat.extend(moved.flattened())
            else:
                flat.append(moved)
        return flat


@dataclass(frozen=True)
class Raw(Node):
    """Pre-built markup — patterns, `<defs>` content, anything the node types
    do not cover. The caller owns escaping and must state the extent (`None`
    for definitions, which occupy no space)."""

    markup: str
    extent: BBox | None = None

    def svg(self) -> str:
        return self.markup

    def bbox(self) -> BBox | None:
        return self.extent

    def transformed(self, t: Transform) -> "Raw":
        raise Unsupported(
            "'Raw' живёт только в SVG: произвольную разметку нельзя ни перенести, "
            "ни нарисовать фигурами — заведи узел в draw/nodes.py"
        )


def arc(
    center: Pt,
    radius: float,
    start_deg: float,
    end_deg: float,
    style: Style = LINE,
) -> Path:
    """Circular arc from `start_deg` to `end_deg` in textbook degrees
    (counter-clockwise positive)."""
    a = polar(center, radius, start_deg)
    b = polar(center, radius, end_deg)
    sweep = 0 if end_deg > start_deg else 1  # y is flipped on screen
    large = 1 if abs(end_deg - start_deg) > 180 else 0
    d = (
        f"M{num(a.x)},{num(a.y)} "
        f"A{num(radius)},{num(radius)} 0 {large} {sweep} {num(b.x)},{num(b.y)}"
    )
    return Path(d, style, extent_points=_arc_samples(center, radius, start_deg, end_deg))


def _arc_samples(center: Pt, radius: float, start_deg: float, end_deg: float) -> tuple[Pt, ...]:
    steps = max(1, math.ceil(abs(end_deg - start_deg) / _ARC_SAMPLE_DEG))
    return tuple(
        polar(center, radius, start_deg + (end_deg - start_deg) * i / steps)
        for i in range(steps + 1)
    )


@dataclass
class PathBuilder:
    """Accumulates path commands and the points they touch.

    Using this instead of formatting a `d` string by hand is what keeps
    curved shapes inside the automatic `viewBox`.
    """

    _parts: list[str] = field(default_factory=list)
    _points: list[Pt] = field(default_factory=list)

    def move(self, p: Pt) -> "PathBuilder":
        self._parts.append(f"M{num(p.x)},{num(p.y)}")
        self._points.append(p)
        return self

    def line(self, p: Pt) -> "PathBuilder":
        self._parts.append(f"L{num(p.x)},{num(p.y)}")
        self._points.append(p)
        return self

    def lines(self, points: Sequence[Pt]) -> "PathBuilder":
        for p in points:
            self.line(p)
        return self

    def arc(self, center: Pt, radius: float, start_deg: float, end_deg: float) -> "PathBuilder":
        """Append an arc, moving to its start if the path is empty."""
        samples = _arc_samples(center, radius, start_deg, end_deg)
        if not self._parts:
            self.move(samples[0])
        end = polar(center, radius, end_deg)
        sweep = 0 if end_deg > start_deg else 1
        large = 1 if abs(end_deg - start_deg) > 180 else 0
        self._parts.append(
            f"A{num(radius)},{num(radius)} 0 {large} {sweep} {num(end.x)},{num(end.y)}"
        )
        self._points.extend(samples)
        return self

    def curve(self, c1: Pt, c2: Pt, end: Pt) -> "PathBuilder":
        self._parts.append(
            f"C{num(c1.x)},{num(c1.y)} {num(c2.x)},{num(c2.y)} {num(end.x)},{num(end.y)}"
        )
        # Control points overstate the extent slightly; a curve never leaves
        # their hull, so the bbox stays correct.
        self._points.extend((c1, c2, end))
        return self

    def close(self) -> "PathBuilder":
        self._parts.append("Z")
        return self

    def build(self, style: Style = LINE) -> Path:
        return Path(" ".join(self._parts), style, tuple(self._points))


def _scaled(style: Style, t: Transform) -> Style:
    """Stroke and font follow the transform, unless the style says otherwise.

    `non_scaling` is the ruling stretched to the column width: its geometry
    changes, its line weight must not.
    """
    if style.non_scaling or t.is_translation:
        return style
    factor = t.scale_factor
    changes: dict[str, object] = {}
    if style.width is not None:
        changes["width"] = style.width * factor
    if style.font_size is not None:
        changes["font_size"] = style.font_size * factor
    return style.with_(**changes) if changes else style


def _move_segments(segments: tuple[Segment, ...], t: Transform) -> list[Segment]:
    keep_arcs = t.is_translation
    moved: list[Segment] = []
    here = Pt(0.0, 0.0)
    for segment in segments:
        if isinstance(segment, Move):
            moved.append(Move(t.apply(segment.to)))
            here = segment.to
        elif isinstance(segment, LineTo):
            moved.append(LineTo(t.apply(segment.to)))
            here = segment.to
        elif isinstance(segment, CurveTo):
            moved.append(CurveTo(t.apply(segment.c1), t.apply(segment.c2), t.apply(segment.to)))
            here = segment.to
        elif isinstance(segment, ArcTo):
            if keep_arcs:
                moved.append(
                    ArcTo(segment.radius, segment.large, segment.sweep, t.apply(segment.to))
                )
            else:
                moved.extend(LineTo(t.apply(point)) for point in sample_arc(here, segment))
            here = segment.to
        else:
            moved.append(Close())
    return moved
