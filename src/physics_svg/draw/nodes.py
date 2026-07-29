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
from physics_svg.draw.style import LINE, Style
from physics_svg.draw.text import num, svg_text, text_width

#: Vertical metrics of the label font as fractions of the font size, used to
#: estimate text extent (see text.text_width for the horizontal counterpart).
_ASCENT = 0.78
_DESCENT = 0.22

#: Arc bounding boxes are sampled rather than solved: five degrees is well
#: below the precision anything downstream needs, and it never mis-handles an
#: arc that crosses an axis.
_ARC_SAMPLE_DEG = 5.0


class Node:
    """Base class. Subclasses are frozen dataclasses."""

    def svg(self) -> str:
        raise NotImplementedError

    def bbox(self) -> BBox | None:
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
        box = BBox(x0, self.at.y - _ASCENT * self.size, x0 + width, self.at.y + _DESCENT * self.size)
        if not self.rotate:
            return box
        return Transform.rotate(self.rotate, about=self.at).apply_box(box)


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
