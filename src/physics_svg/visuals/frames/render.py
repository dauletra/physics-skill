"""Drawing one motion twice: as the carrier sees it, as the ground sees it.

Both frames are built in cells with y upwards — the orientation a student
draws in — and turned into user units by one multiplication, so nothing here
flips a sign twice. The body starts at the origin of its frame; the carrier
is drawn at that origin and the ground below it.

**One cell for both frames.** Comparability is a property of the pair, not of
either picture: a parabola drawn at one scale beside a segment drawn at
another would lie about the very thing the drawing exists to show. So the
cell is chosen from the two frames together, and each frame is then a group
translated into place.

**The arrangement is measured, not authored.** Side by side or one above the
other, whichever comes out closer to the proportion of a figure — and a frame
counts as wide as its caption when its caption is wider than its border,
because that overhang is what would run into the neighbouring frame.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from physics_svg.draw import (
    BLACK,
    BODY,
    FRAME,
    LINE,
    BBox,
    Canvas,
    Circle,
    Group,
    Line,
    Medium,
    Node,
    Pt,
    Rect,
    Style,
    Text,
    Transform,
    text_width,
)
from physics_svg.elements import MARK_RADIUS, arrow, label_near, strobe
from physics_svg.visuals.frames.model import FramesSpec
from physics_svg.visuals.registry import Layout

#: Target extent of the whole drawing in user units, and the bounds a cell may
#: take — the same reasoning and nearly the same numbers as a vector diagram,
#: so that a cell means the same thing on both.
TARGET_EXTENT = 150.0
MIN_CELL = 7.0
MAX_CELL = 22.0

#: The carrier, in cells: a platform half a cell thick on quarter-cell wheels,
#: so its top — where the body starts — stands a whole cell above the ground
#: and the picture keeps counting in whole cells.
CARRIER_HEIGHT = 0.5
WHEEL_RADIUS = 0.25
CARRIER_TOP = CARRIER_HEIGHT + 2 * WHEEL_RADIUS

#: Half-width of a carrier nothing travels along, and the overhang it keeps
#: beyond a body that does travel along it.
CARRIER_HALF = 1.1
CARRIER_MARGIN = 0.6

#: How far below the ground the arrow of the carrier's displacement runs.
SHIFT_DROP = 0.7

#: Slack between the drawn content and the border of a frame, in cells.
FRAME_PAD = 0.5

#: Length of one axis of the frame's own reference cross, in cells, and the
#: head it ends in. Short on purpose: the axes say where the origin is and
#: which way x and y run — the counting is done off the grid, so an axis
#: spanning the whole frame would only be a second grid line with a name.
AXIS_LENGTH = 2.2
AXIS_HEAD = 5.0

#: Gaps between the two frames, in cells.
GAP_ACROSS = 1.4
GAP_DOWN = 1.0

#: The proportion an arrangement is judged against: a figure on a sheet and a
#: picture on a slide are both wider than tall, and neither wants a ribbon.
TARGET_ASPECT = 1.5

#: Everything that clears a label is measured in label heights, so a larger
#: medium moves the writing away instead of into the picture.
_TITLE_DROP = 1.5
_TITLE_SPACE = 2.0
_CAPTION_DROP = 1.4

#: How much of the closest gap between two positions a mark may take up, and
#: the radius below which it stops being a mark at all. A row that crowds is
#: the point of a stroboscopic trail — a row that merges into a bar is not.
MARK_SHARE = 0.4
MIN_MARK = 1.2

_TRAIL = LINE
#: The reference cross is service geometry, like the grid: it is there to be
#: read *under* the drawing, so the trail crossing it stays the black thing
#: on the page and an axis head beside a mark cannot be mistaken for one.
_AXIS = Style(width=0.9, fill="none")
_GROUND = Style(stroke=BLACK, width=1.0, fill="none")
_SHIFT = Style(stroke=BLACK, width=1.1, fill="none")
_GRID = Style(width=0.5, fill="none")


@dataclass(frozen=True)
class Panel:
    """One frame of reference, drawn in its own coordinates."""

    nodes: tuple[Node, ...]
    box: BBox
    title: str


def render(model: FramesSpec, canvas: Canvas) -> Layout:
    cell = _cell_size(model)
    radius = _mark_radius(model, cell)
    medium = canvas.medium
    panels = [
        _panel(model, cell, radius, medium, moving=False),
        _panel(model, cell, radius, medium, moving=True),
    ]
    offsets = _arrangement(panels, cell, medium)
    side_by_side = offsets[0][1] == offsets[1][1]
    # Captions of frames standing side by side share one line, under the
    # lower of them: they name the halves of one picture, not two pictures.
    shared = max(panel.box.y1 + dy for panel, (_dx, dy) in zip(panels, offsets))

    for panel, (dx, dy) in zip(panels, offsets):
        canvas.add(Group(panel.nodes, Transform.translate(dx, dy)))
    for panel, (dx, dy) in zip(panels, offsets):
        baseline = shared if side_by_side else panel.box.y1 + dy
        canvas.add(
            Text(
                Pt(panel.box.center.x + dx, baseline + _TITLE_DROP * medium.caption),
                panel.title,
                medium.caption,
                "middle",
            )
        )
    if model.caption:
        box = canvas.content_box()
        if box is not None:
            canvas.add(
                Text(
                    Pt(box.center.x, box.y1 + _CAPTION_DROP * medium.caption),
                    model.caption,
                    medium.caption,
                    "middle",
                )
            )
    return Layout(padding=2.0)


# --- one frame ----------------------------------------------------------


def _panel(
    model: FramesSpec, cell: float, radius: float, medium: Medium, *, moving: bool
) -> Panel:
    """The scene as one frame of reference sees it.

    `moving` is the ground frame — the one the carrier travels across, where
    every position of the body carries the carrier's own progress with it.
    """
    positions = _positions(model, moving=moving)
    ground = _ground_level(model)
    carriers = [(0.0, True), (model.shift, False)] if moving else [(0.0, False)]
    region = _region(model, positions, carriers, cell, moving=moving)

    nodes: list[Node] = []
    if model.grid:
        nodes.extend(_grid(region, cell, medium))
    nodes.append(
        Rect(
            Pt(region.x0, region.y0),
            region.width,
            region.height,
            FRAME.with_(stroke=medium.rule),
        )
    )
    nodes.append(Line(Pt(region.x0, -ground * cell), Pt(region.x1, -ground * cell), _GROUND))
    if model.axes:
        # Before the carriers: the axes belong to the frame, and a body of
        # reference standing on them covers them, as it would on paper.
        nodes.extend(_axes(region, cell, medium))
    for offset, faded in carriers:
        nodes.extend(_carrier(model, offset, cell, medium, faded=faded))
    if moving:
        level = (ground - SHIFT_DROP) * cell
        nodes.extend(arrow(Pt(0.0, -level), Pt(model.shift * cell, -level), _SHIFT))
    nodes.extend(
        strobe([_at(point, cell) for point in positions], radius=radius, style=_TRAIL)
    )

    title = f"система отсчёта: {model.ground if moving else model.carrier}"
    return Panel(tuple(nodes), region, title)


def _positions(model: FramesSpec, *, moving: bool) -> list[tuple[float, float]]:
    """Where the body is at each mark, in the frame asked for.

    The ground frame is the carrier frame plus `shift·t` — the Galilean
    transform, applied to the stroboscopic row rather than to a curve.
    """
    positions = model.positions
    if not moving:
        return positions
    span = len(positions) - 1
    return [(x + model.shift * step / span, y) for step, (x, y) in enumerate(positions)]


def _region(
    model: FramesSpec,
    positions: list[tuple[float, float]],
    carriers: list[tuple[float, bool]],
    cell: float,
    *,
    moving: bool,
) -> BBox:
    """The frame's border, snapped out to whole cells so that the lattice
    inside it meets its edges."""
    ground = _ground_level(model)
    left, right = _carrier_span(model)
    xs = [x for x, _ in positions] + [left + offset for offset, _ in carriers]
    xs += [right + offset for offset, _ in carriers]
    ys = [y for _, y in positions] + [ground]
    if moving:
        ys.append(ground - SHIFT_DROP)
    if _airborne(model):
        ys.append(max(y for _, y in positions) + CARRIER_HEIGHT)
    if model.axes:
        # The reference cross has to fit inside its own frame, names and all.
        xs.append(AXIS_LENGTH)
        ys.append(AXIS_LENGTH)
    return BBox(
        math.floor(min(xs) - FRAME_PAD) * cell,
        -math.ceil(max(ys) + FRAME_PAD) * cell,
        math.ceil(max(xs) + FRAME_PAD) * cell,
        -math.floor(min(ys) - FRAME_PAD) * cell,
    )


def _at(point: tuple[float, float], cell: float) -> Pt:
    """A point in cells, y upwards, as user units on the screen."""
    return Pt(point[0] * cell, -point[1] * cell)


def _airborne(model: FramesSpec) -> bool:
    """Is the carrier above the ground rather than standing on it?"""
    return model.motion == "drop"


def _ground_level(model: FramesSpec) -> float:
    """Where the ground runs, in cells from the body's starting point."""
    if _airborne(model):
        assert model.rise is not None
        return -model.rise
    return -CARRIER_TOP


def _carrier_span(model: FramesSpec) -> tuple[float, float]:
    """The carrier's own extent in cells: wide enough to hold whatever
    travels along it, never narrower than a cart."""
    xs = [x for x, _ in model.positions]
    return min(min(xs) - CARRIER_MARGIN, -CARRIER_HALF), max(max(xs) + CARRIER_MARGIN, CARRIER_HALF)


def _carrier(
    model: FramesSpec, offset: float, cell: float, medium: Medium, *, faded: bool
) -> list[Node]:
    """A platform on wheels — or, in the air, a platform without them.

    Not a carriage, not an aeroplane, not a boat: what the picture needs is a
    body of reference, and which object it stands for is what the frame's
    caption says. Drawing the object would mean drawing every object.
    """
    left, right = _carrier_span(model)
    style = Style(stroke=medium.ruling, width=1.0, fill="none") if faded else BODY
    top = CARRIER_HEIGHT if _airborne(model) else 0.0
    nodes: list[Node] = [
        Rect(
            _at((left + offset, top), cell),
            (right - left) * cell,
            CARRIER_HEIGHT * cell,
            style,
        )
    ]
    if not _airborne(model):
        axle = -CARRIER_HEIGHT - WHEEL_RADIUS
        for side in (left + CARRIER_MARGIN, right - CARRIER_MARGIN):
            nodes.append(Circle(_at((side + offset, axle), cell), WHEEL_RADIUS * cell, style))
    return nodes


def _axes(region: BBox, cell: float, medium: Medium) -> list[Node]:
    """The frame's own axes, crossing at the point the body started from.

    Both frames put their origin there, because at the first mark the two
    origins coincide — and what the picture then shows is that one of them
    stays put while the carrier drives away from it with the other.

    The axes carry no numbers. A cell is the division here and lengths are
    counted off the grid; a numbered scale would be right only where the
    coordinate itself is data of the exercise, and no exercise has asked for
    that yet (docs/frames.md, «Координатные оси»).
    """
    origin = Pt(0.0, 0.0)
    end_x = _at((AXIS_LENGTH, 0.0), cell)
    end_y = _at((0.0, AXIS_LENGTH), cell)
    size = medium.caption
    # Three labels around one point, so each is pushed to a side of its own:
    # the names above their heads, the zero back along the diagonal between
    # the two axes, where neither the trail nor the carrier goes.
    style = _AXIS.with_(stroke=medium.rule)
    return [
        *arrow(origin, end_x, style, AXIS_HEAD),
        *arrow(origin, end_y, style, AXIS_HEAD),
        label_near(end_x, Pt(0.0, -1.0), "x", size),
        label_near(end_y, Pt(1.0, 0.0), "y", size),
        label_near(origin, Pt(-1.0, -1.0), "0", size),
    ]


def _grid(region: BBox, cell: float, medium: Medium) -> list[Node]:
    """A lattice filling the frame, aligned to the origin rather than to the
    border: lengths are counted from where the body started."""
    style = _GRID.with_(stroke=medium.ruling)
    nodes: list[Node] = []
    for step in range(math.ceil(region.x0 / cell), math.floor(region.x1 / cell) + 1):
        nodes.append(Line(Pt(step * cell, region.y0), Pt(step * cell, region.y1), style))
    for step in range(math.ceil(region.y0 / cell), math.floor(region.y1 / cell) + 1):
        nodes.append(Line(Pt(region.x0, step * cell), Pt(region.x1, step * cell), style))
    return nodes


# --- the pair -----------------------------------------------------------


def _cell_size(model: FramesSpec) -> float:
    """One cell for both frames, sized so the pair fits the page.

    The pair is about twice one frame in whichever direction it is laid out,
    and that doubling is what has to fit — which of the two directions it
    lands in is decided later, from the finished frames.
    """
    xs = [x for x, _ in model.positions]
    ys = [y for _, y in model.positions]
    left, right = _carrier_span(model)
    width = max(right, max(xs)) - min(left, min(xs)) + abs(model.shift)
    height = max(ys) - min(min(ys), _ground_level(model)) + CARRIER_TOP
    extent = 2.0 * max(width, height, 1e-6)
    return max(MIN_CELL, min(MAX_CELL, TARGET_EXTENT / extent))


def _mark_radius(model: FramesSpec, cell: float) -> float:
    """How large one position of the body is drawn, in user units.

    One radius for both frames — it is one body — and it follows the tightest
    gap the trail has anywhere: at the top of a toss and at the start of a
    fall the marks close in, and that closing in *is* the statement. Marks of
    a fixed size would there merge into a bar and say nothing.
    """
    gaps = [
        (_at(other, cell) - _at(one, cell)).length()
        for moving in (False, True)
        for one, other in zip(
            _positions(model, moving=moving), _positions(model, moving=moving)[1:]
        )
    ]
    tightest = min((gap for gap in gaps if gap > 1e-9), default=0.0)
    if not tightest:
        return MARK_RADIUS
    return max(MIN_MARK, min(MARK_RADIUS, MARK_SHARE * tightest))


def _arrangement(panels: list[Panel], cell: float, medium: Medium) -> list[tuple[float, float]]:
    """Where each frame goes: side by side, or one above the other.

    Decided from the **frames themselves**, in cells — never from how wide
    their captions come out. A picture that rearranged itself between the
    sheet and the board would be two drawings, and the labels are the only
    thing the medium is allowed to change (`draw/medium.py`).
    """
    widths = [panel.box.width for panel in panels]
    heights = [panel.box.height for panel in panels]
    across = (sum(widths) + GAP_ACROSS * cell, max(heights))
    down = (max(widths), sum(heights) + GAP_DOWN * cell)
    if _mismatch(across) <= _mismatch(down):
        gap = _across_gap(panels, widths, cell, medium)
        total = sum(widths) + gap
        return [
            (-total / 2 + widths[0] / 2 - panels[0].box.center.x, 0.0),
            (total / 2 - widths[1] / 2 - panels[1].box.center.x, 0.0),
        ]
    # Stacked frames keep the same x origin, so the two starting points line
    # up and the carrier's displacement reads as the offset between them.
    below = panels[0].box.y1 + _TITLE_SPACE * medium.caption + GAP_DOWN * cell
    return [(0.0, 0.0), (0.0, below - panels[1].box.y0)]


def _across_gap(
    panels: list[Panel], widths: list[float], cell: float, medium: Medium
) -> float:
    """How far apart two frames standing side by side have to be.

    Wide enough for the frames, and wide enough that their captions clear
    each other: each caption is centred on its own frame, so what has to fit
    between the centres is half of each of them. This is the one place a
    label moves geometry — and it moves the gap, not the arrangement.
    """
    titles = [text_width(panel.title, medium.caption) for panel in panels]
    slack = GAP_ACROSS * cell
    return max(slack, sum(titles) / 2 - sum(widths) / 2 + slack)


def _mismatch(size: tuple[float, float]) -> float:
    width, height = size
    return abs(math.log((width / height) / TARGET_ASPECT)) if height else math.inf
