"""Drawing a vector diagram.

The cell is the unit of the picture: every length is a number of cells, and
the renderer only decides how large a cell is on paper — small enough that
the drawing fits, large enough that it stays legible. That is why two forces
written as 3 and 4 always come out in a 3:4 ratio, whatever else is on the
diagram.

Geometry is built in cells and in screen orientation throughout: `polar()`
already turns a textbook angle into screen coordinates, so nothing here
flips a sign, and scaling to user units is one multiplication at the end.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence

from physics_svg.draw import (
    BLACK,
    BODY,
    DASH,
    GREY,
    HEAVY,
    SOLID,
    BBox,
    Canvas,
    Circle,
    Line,
    Node,
    Pt,
    Rect,
    Style,
    Text,
    polar,
)
from physics_svg.elements import angle_mark, arrow, label_near
from physics_svg.visuals.registry import Layout
from physics_svg.visuals.vectors.model import ArrowSpec, VectorsSpec

#: Target extent of the drawing in user units, and the bounds a cell may
#: take: smaller than the minimum stops being countable, larger than the
#: maximum makes a two-vector picture fill the page.
TARGET_EXTENT = 130.0
MIN_CELL = 9.0
MAX_CELL = 26.0

#: Half-size of the body at the point of application, in cells.
BODY_RADIUS = 0.55

#: How far aside a common-origin resultant is drawn, in cells.
RESULTANT_OFFSET = 0.75

#: The angle label leans towards the first arm rather than sitting exactly on
#: the bisector — which is where a resultant tends to run.
ANGLE_LABEL_BIAS = 0.3

_VECTOR = HEAVY
_CONSTRUCTION = Style(stroke=BLACK, width=1.0, dash=DASH["dashed"], fill="none")
_RESULTANT = Style(stroke=BLACK, width=2.6, fill="none")
_GRID = Style(stroke=GREY, width=0.5, fill="none")
_PARALLELOGRAM = Style(stroke=GREY, width=0.9, dash=DASH["dashed"], fill="none")
_CAPTION_SIZE = 8.0


@dataclass(frozen=True)
class Placed:
    """One vector after its position is worked out, in cells."""

    spec: ArrowSpec
    start: Pt
    end: Pt

    @property
    def direction(self) -> Pt:
        span = self.end - self.start
        return span if span.length() else Pt(1.0, 0.0)


def render(model: VectorsSpec, canvas: Canvas) -> Layout:
    placed = _place(model)
    resultant = _resultant(model, placed)
    cell = _cell_size(placed, resultant)

    def at(point: Pt) -> Pt:
        return point * cell

    if model.grid:
        canvas.extend(_grid(placed, resultant, cell))
    if model.body is not None:
        canvas.extend(_body(model.body, cell))

    for item in placed:
        style = _CONSTRUCTION if item.spec.style == "dashed" else _VECTOR
        canvas.extend(arrow(at(item.start), at(item.end), style))
        if item.spec.label:
            canvas.add(label_near(at(item.end), item.direction, item.spec.label))

    if resultant is not None:
        if model.arrangement == "parallelogram":
            canvas.extend(_parallelogram(placed, resultant, cell))
        start, end = at(resultant.start), at(resultant.end)
        aside = _aside(resultant.direction)
        if model.arrangement == "common":
            # Forces from one point are often collinear with their own sum —
            # drawn in place, the resultant would hide under one of them.
            shift = aside * (RESULTANT_OFFSET * cell)
            start, end = start + shift, end + shift
        # Labelled at the middle, not at the head: in a chain the resultant
        # ends exactly where the last vector does, and the two labels would
        # sit on top of each other.
        canvas.extend(arrow(start, end, _RESULTANT))
        canvas.add(label_near(start.lerp(end, 0.5), aside, model.resultant or ""))

    canvas.extend(_angles(model, placed, cell))

    if model.caption:
        box = canvas.content_box()
        if box is not None:
            canvas.add(
                Text(Pt(box.center.x, box.y1 + 11), model.caption, _CAPTION_SIZE, "middle")
            )
    return Layout(padding=3.0)


# --- geometry -----------------------------------------------------------


ORIGIN = Pt(0.0, 0.0)


def _place(model: VectorsSpec) -> list[Placed]:
    """Where each vector starts and ends, in cells."""
    placed: list[Placed] = []
    tail = ORIGIN
    for spec in model.vectors:
        start = tail if model.arrangement == "chain" else ORIGIN
        placed.append(Placed(spec, start, polar(start, spec.length, spec.angle)))
        tail = placed[-1].end
    return placed


def _resultant(model: VectorsSpec, placed: list[Placed]) -> Placed | None:
    """The sum, as one more vector to draw.

    A chain sums from the tail of the first to the head of the last; from a
    common origin it starts where the others do.
    """
    if model.resultant is None:
        return None
    length, angle = model.sum
    start = placed[0].start
    spec = ArrowSpec(length=length, angle=angle, label=model.resultant)
    return Placed(spec, start, polar(start, length, angle))


def _aside(along: Pt) -> Pt:
    """The side a label or an offset copy goes to: below a rightward vector,
    consistently to one hand of any other."""
    return -along.normalized().perpendicular()


def _points(placed: Sequence[Placed], resultant: Placed | None) -> list[Pt]:
    items = list(placed) + ([resultant] if resultant else [])
    return [point for item in items for point in (item.start, item.end)]


def _cell_size(placed: list[Placed], resultant: Placed | None) -> float:
    box = BBox.of(_points(placed, resultant))
    extent = max(box.width, box.height, 1e-6) if box else 1.0
    return max(MIN_CELL, min(MAX_CELL, TARGET_EXTENT / extent))


# --- parts --------------------------------------------------------------


def _grid(placed: list[Placed], resultant: Placed | None, cell: float) -> list[Node]:
    """A lattice covering the drawing, so lengths can be counted off it."""
    box = BBox.of(_points(placed, resultant))
    if box is None:
        return []
    left, right = math.floor(box.x0) - 1, math.ceil(box.x1) + 1
    top, bottom = math.floor(box.y0) - 1, math.ceil(box.y1) + 1
    nodes: list[Node] = []
    for x in range(left, right + 1):
        nodes.append(Line(Pt(x * cell, top * cell), Pt(x * cell, bottom * cell), _GRID))
    for y in range(top, bottom + 1):
        nodes.append(Line(Pt(left * cell, y * cell), Pt(right * cell, y * cell), _GRID))
    return nodes


def _body(kind: str, cell: float) -> list[Node]:
    size = BODY_RADIUS * cell
    if kind == "point":
        return [Circle(ORIGIN, 3.0, SOLID)]
    if kind == "ball":
        return [Circle(ORIGIN, size, BODY)]
    return [Rect(Pt(-size, -size), size * 2, size * 2, BODY)]


def _parallelogram(placed: list[Placed], resultant: Placed, cell: float) -> list[Node]:
    """The two dashed sides that close the parallelogram."""
    first, second = placed
    corner = resultant.end * cell
    return [
        Line(first.end * cell, corner, _PARALLELOGRAM),
        Line(second.end * cell, corner, _PARALLELOGRAM),
    ]


def _angles(model: VectorsSpec, placed: list[Placed], cell: float) -> list[Node]:
    by_id = {item.spec.id: item for item in placed if item.spec.id}
    nodes: list[Node] = []
    for i, mark in enumerate(model.angles):
        first, second = (by_id[reference] for reference in mark.between)
        # The radius follows the shorter arm, so an arc never overshoots it;
        # stacked marks step outwards.
        radius = min(first.spec.length, second.spec.length) * cell * 0.34 + i * 4.0
        nodes.extend(
            angle_mark(
                first.start * cell, first.spec.angle, second.spec.angle, radius, mark.label
            )
        )
    return nodes
