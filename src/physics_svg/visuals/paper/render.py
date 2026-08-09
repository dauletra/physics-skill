"""Drawing the five rulings.

Squared, graph-paper and dotted rulings are painted with an SVG pattern:
a 12x12 cm graph-paper field would otherwise be some 240 explicit lines,
repeated for every field on the page. Patterns need element ids, which used
to be a reason to avoid them — `canvas.define()` scopes ids per block, so
two fields on one page can no longer collide.

**Only `plain` is framed.** A writing area is ruling, not a box drawn on the
sheet, so nothing is outlined: lines and dots end where the ruling ends, and
squares close their own last cell. `plain` is the exception because there the
border is the whole content — an empty field says how far to draw only by
being bounded.

Lines and plain fields have no horizontal geometry, so without `cols` they
stretch to the column width. A stretched field is scaled anisotropically,
which would make the vertical sides of a frame a different weight from the
horizontal ones — hence the non-scaling stroke on the fluid `plain`.
"""

from __future__ import annotations

from typing import Callable

from physics_svg.draw import (
    BBox,
    Canvas,
    Circle,
    Line,
    Medium,
    Node,
    Path,
    Pt,
    Rect,
    Style,
    num,
)
from physics_svg.draw.canvas import SCREEN_SCALE
from physics_svg.visuals.paper.model import STEPS, PaperSpec
from physics_svg.visuals.registry import Layout

#: A ruling is a guide, not a contour: it must stay behind what the student
#: writes on top of it. The weights below are the drawing's and never change;
#: the grey each one is drawn in comes off the canvas, because how weak a
#: service line may be is the destination's business (draw/medium.py).
_FRAME = Style(width=0.7, fill="none")
_FRAME_FLUID = Style(width=1.0, fill="none", non_scaling=True)
_WRITING_LINE = Style(
    stroke="#000", width=1.0, dash="1,3", fill="none", non_scaling=True
)
#: The weights the squared rulings close themselves with — the line of the
#: cell itself, so the edge of the field is not heavier than what is inside it.
_GRID_EDGE = Style(width=0.5, fill="none")
_MM_EDGE = Style(width=0.8, fill="none")

#: Half a unit of slack: the outermost line sits on the edge of the field, and
#: its stroke would be cut in half by the frame of the SVG without it.
_PADDING = 0.5


def render(model: PaperSpec, canvas: Canvas) -> Layout:
    width, height = model.width, model.height
    _PAINTERS[model.ruling](model, canvas, width, height)
    if model.cols is not None:
        return Layout(padding=_PADDING)
    # No width in the data: the field takes the whole column, and its height
    # must stay exactly what the author asked for even in a narrow column.
    return Layout(
        padding=_PADDING,
        viewbox=BBox(-_PADDING, -_PADDING, width + _PADDING, height + _PADDING),
        fluid_height=(height + 1) * SCREEN_SCALE,
    )


def _paint_lines(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Writing lines, like a lined exercise book: a rule at the foot of every
    row. No pattern — rows are counted in tens, and explicit lines survive
    being stretched to the column width."""
    step = STEPS["lines"]
    for i in range(1, round(height / step) + 1):
        canvas.add(Line(Pt(0, step * i), Pt(width, step * i), _WRITING_LINE))


def _paint_plain(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """An empty framed field — room for a drawing, a diagram, free writing.

    The one ruling that keeps its border: with no lines of its own, an empty
    field says how far the drawing may go only by being bounded.
    """
    canvas.add(_frame(canvas.medium, width, height, fluid=model.cols is None))


def _paint_grid(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Exercise-book squares: one level of lines."""
    step = STEPS["grid"]
    cell = canvas.tiling(
        "grid",
        step,
        step,
        [Path(f"M{step} 0 L0 0 0 {step}", _GRID_EDGE.with_(stroke=canvas.medium.ruling))],
    )
    canvas.add(
        canvas.fill_tiled(BBox(0, 0, width, height), cell),
        *_closing_edges(width, height, _GRID_EDGE.with_(stroke=canvas.medium.ruling)),
    )


def _paint_dots(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Dots at the lattice nodes — the same grid, but not crossing out the
    construction drawn over it. The dot sits at the centre of the pattern
    cell, so the lattice ends whole and needs nothing to close it."""
    step = STEPS["dots"]
    half = step / 2
    cell = canvas.tiling(
        "dots", step, step, [Circle(Pt(half, half), 0.8, Style(fill=canvas.medium.ruling))]
    )
    canvas.add(canvas.fill_tiled(BBox(0, 0, width, height), cell))


def _paint_mm(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Graph paper, with the three line weights of the real thing: fine every
    millimetre, medium every 5 mm, heavy every centimetre. Built as nested
    patterns — the large cell is filled with the fine one — so the markup
    does not grow with the area of the field."""
    major = STEPS["mm"]
    fine, mid = major / 10, major / 2
    millimetres = canvas.tiling(
        "mm-fine",
        fine,
        fine,
        [
            Path(
                f"M{num(fine)} 0 L0 0 0 {num(fine)}",
                Style(fill="none", stroke=canvas.medium.grid_fine, width=0.3),
            )
        ],
    )
    centimetres = canvas.tiling(
        "mm",
        major,
        major,
        [
            Path(
                f"M{num(mid)} 0 L{num(mid)} {major} M0 {num(mid)} L{major} {num(mid)}",
                Style(fill="none", stroke=canvas.medium.ruling, width=0.4),
            ),
            Path(
                f"M{major} 0 L0 0 0 {major}",
                Style(fill="none", stroke=canvas.medium.rule, width=0.8),
            ),
        ],
        base=millimetres,
    )
    canvas.add(
        canvas.fill_tiled(BBox(0, 0, width, height), centimetres),
        *_closing_edges(width, height, _MM_EDGE.with_(stroke=canvas.medium.rule)),
    )


def _closing_edges(width: float, height: float, style: Style) -> tuple[Node, Node]:
    """The last cell of a squared ruling, closed.

    A pattern cell is drawn along its top and left, so the far right and the
    foot of the field are the two lines no tile ever paints. They are drawn in
    the weight of the ruling itself: this finishes the squares, it does not
    put a border around the writing area.
    """
    return (
        Line(Pt(width, 0), Pt(width, height), style),
        Line(Pt(0, height), Pt(width, height), style),
    )


def _frame(medium: Medium, width: float, height: float, fluid: bool = False) -> Node:
    style = _FRAME_FLUID if fluid else _FRAME
    return Rect(Pt(0, 0), width, height, style.with_(stroke=medium.rule))


_PAINTERS: dict[str, Callable[[PaperSpec, Canvas, float, float], None]] = {
    "lines": _paint_lines,
    "plain": _paint_plain,
    "grid": _paint_grid,
    "dots": _paint_dots,
    "mm": _paint_mm,
}
