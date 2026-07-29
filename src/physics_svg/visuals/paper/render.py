"""Drawing the five rulings.

Squared, graph-paper and dotted rulings are painted with an SVG pattern:
a 12x12 cm graph-paper field would otherwise be some 240 explicit lines,
repeated for every field on the page. Patterns need element ids, which used
to be a reason to avoid them — `canvas.define()` scopes ids per block, so
two fields on one page can no longer collide.

Lines and plain fields have no horizontal geometry, so without `cols` they
stretch to the column width. A stretched field is scaled anisotropically,
which would make the vertical sides of its frame a different weight from the
horizontal ones — hence the non-scaling stroke on exactly those rulings.
"""

from __future__ import annotations

from typing import Callable

from physics_svg.draw import (
    GREY,
    GREY_FAINT,
    GREY_STRONG,
    BBox,
    Canvas,
    Line,
    Node,
    Pt,
    Rect,
    Style,
    num,
)
from physics_svg.draw.canvas import SCREEN_SCALE
from physics_svg.visuals.paper.model import STEPS, PaperSpec
from physics_svg.visuals.registry import Layout

#: A ruling is a guide, not a contour: it must stay behind what the student
#: writes on top of it.
_FRAME = Style(stroke=GREY_STRONG, width=0.7, fill="none")
_FRAME_FLUID = Style(stroke=GREY_STRONG, width=1.0, fill="none", non_scaling=True)
_WRITING_LINE = Style(
    stroke="#000", width=1.0, dash="1,3", fill="none", non_scaling=True
)

#: Half a unit of slack: the frame sits on the edge of the field, and its
#: stroke would be cut in half by the frame of the SVG without it.
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
    canvas.add(_frame(width, height, fluid=model.cols is None))


def _paint_plain(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """An empty framed field — room for a drawing, a diagram, free writing."""
    canvas.add(_frame(width, height, fluid=model.cols is None))


def _paint_grid(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Exercise-book squares: one level of lines."""
    step = STEPS["grid"]
    pattern = canvas.define(
        "grid",
        lambda pid: (
            f'<pattern id="{pid}" width="{step}" height="{step}" '
            f'patternUnits="userSpaceOnUse">'
            f'<path d="M{step} 0 L0 0 0 {step}" fill="none" stroke="{GREY}" '
            'stroke-width="0.5"/></pattern>'
        ),
    )
    canvas.add(_filled(width, height, pattern), _frame(width, height))


def _paint_dots(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Dots at the lattice nodes — the same grid, but not crossing out the
    construction drawn over it. The dot sits at the centre of the pattern
    cell so the frame does not clip it in half at the edge."""
    step = STEPS["dots"]
    half = num(step / 2)
    pattern = canvas.define(
        "dots",
        lambda pid: (
            f'<pattern id="{pid}" width="{step}" height="{step}" '
            f'patternUnits="userSpaceOnUse">'
            f'<circle cx="{half}" cy="{half}" r="0.8" fill="{GREY}"/></pattern>'
        ),
    )
    canvas.add(_filled(width, height, pattern), _frame(width, height))


def _paint_mm(model: PaperSpec, canvas: Canvas, width: float, height: float) -> None:
    """Graph paper, with the three line weights of the real thing: fine every
    millimetre, medium every 5 mm, heavy every centimetre. Built as nested
    patterns — the large cell is filled with the fine one — so the markup
    does not grow with the area of the field."""
    major = STEPS["mm"]
    fine, mid = major / 10, major / 2
    fine_pattern = canvas.define(
        "mm-fine",
        lambda pid: (
            f'<pattern id="{pid}" width="{num(fine)}" height="{num(fine)}" '
            f'patternUnits="userSpaceOnUse">'
            f'<path d="M{num(fine)} 0 L0 0 0 {num(fine)}" fill="none" '
            f'stroke="{GREY_FAINT}" stroke-width="0.3"/></pattern>'
        ),
    )
    pattern = canvas.define(
        "mm",
        lambda pid: (
            f'<pattern id="{pid}" width="{major}" height="{major}" '
            f'patternUnits="userSpaceOnUse">'
            f'<rect width="{major}" height="{major}" fill="url(#{fine_pattern})"/>'
            f'<path d="M{num(mid)} 0 L{num(mid)} {major} M0 {num(mid)} '
            f'L{major} {num(mid)}" fill="none" stroke="{GREY}" stroke-width="0.4"/>'
            f'<path d="M{major} 0 L0 0 0 {major}" fill="none" stroke="{GREY_STRONG}" '
            'stroke-width="0.8"/></pattern>'
        ),
    )
    canvas.add(_filled(width, height, pattern), _frame(width, height))


def _filled(width: float, height: float, pattern_id: str) -> Node:
    return Rect(Pt(0, 0), width, height, Style(fill=f"url(#{pattern_id})"))


def _frame(width: float, height: float, fluid: bool = False) -> Node:
    return Rect(Pt(0, 0), width, height, _FRAME_FLUID if fluid else _FRAME)


_PAINTERS: dict[str, Callable[[PaperSpec, Canvas, float, float], None]] = {
    "lines": _paint_lines,
    "plain": _paint_plain,
    "grid": _paint_grid,
    "dots": _paint_dots,
    "mm": _paint_mm,
}
