"""Drawing a graph: grid, axes with their ticks, series, legend.

Divisions are computed once per axis and everything reads off that one list:
a gridline, a tick on the axis and a number are three ways of showing the
same division, so they cannot drift apart. The ticks themselves are drawn by
`scale_marks`, the element that rules an instrument scale — an axis of a
graph and the edge of a ruler are numbered by the same code.

The plot area is a fixed rectangle so that graphs on one page share a shape;
everything else — tick labels, axis captions, the arrows the axes end in, the
legend — extends the frame around it, and the canvas measures the result. Long
y-axis numbers therefore widen the picture instead of being clipped, and
nothing but the data is ever drawn inside the rectangle.

The legend is drawn **inside** the SVG. It used to be HTML beside the
picture, with a second copy in the standalone renderer for slides; one
drawing means one implementation, and the file explains itself wherever it
is pasted.
"""

from __future__ import annotations

from typing import Callable, Sequence

from physics_svg.draw import (
    BLACK,
    DASH,
    GRID,
    GRID_FINE,
    HEAVY,
    WHITE,
    Canvas,
    Circle,
    Line,
    Node,
    PathBuilder,
    Polyline,
    Pt,
    Rect,
    Style,
    Text,
    num,
    text_width,
)
from physics_svg.elements import (
    LinearAxis,
    Tick,
    arrow,
    division_values,
    label_every,
    nice_ticks,
    scale_marks,
    subdivisions,
    ticks_at,
)
from physics_svg.visuals.graph.model import (
    MIN_LABEL_GAP_X,
    MIN_LABEL_GAP_Y,
    PLOT_HEIGHT,
    PLOT_WIDTH,
    GraphSpec,
    SeriesSpec,
)
from physics_svg.visuals.registry import Layout

_TICK_LABEL_SIZE = 9.0
_AXIS_LABEL_SIZE = 10.0
_LEGEND_SIZE = 7.0

#: Tick lengths on an axis: a numbered division earns a longer stroke, the
#: way it does on any instrument scale.
_TICK_MAJOR = 4.0
_TICK_MINOR = 2.5

#: How far a number sits from the axis it belongs to — past the tick, with
#: room to breathe.
_LABEL_DISTANCE_X = 13.0
_LABEL_DISTANCE_Y = 7.5

#: Numbers beside a horizontal tick sit on it, not under it.
_LABEL_SHIFT_Y = 3.0

#: How far each axis runs past the plot rectangle, and the head it ends in.
#: The head has to clear the last division line — sitting on it, it would read
#: as a mark of the grid rather than as a direction — and it is smaller than a
#: vector's: an axis points, it does not act. The vertical overshoot is the
#: longer one: the plot is half as tall as it is wide, so the same length
#: reads as shorter on the y axis.
_OVERSHOOT_X = 10.0
_OVERSHOOT_Y = 14.0
_AXIS_HEAD = 5.5

#: Gap between the tip of an axis and the quantity named after it.
_CAPTION_GAP = 3.0

#: Densest numbering the renderer will choose on its own when the author pins
#: the division but not the labels. The limit is legibility, the same one the
#: model validates a pinned label step against.
_MAX_LABELS_X = int(PLOT_WIDTH // MIN_LABEL_GAP_X) + 1
_MAX_LABELS_Y = int(PLOT_HEIGHT // MIN_LABEL_GAP_Y) + 1

#: Marker shapes cycle per series: a scatter plot distinguishes series by
#: marker, not by line, because there is no line to dash.
MARKER_SHAPES = ("circle", "cross", "triangle")

_SERIES_LINE = Style(stroke=BLACK, width=2.0, fill="none")
_BAR = Style(stroke=BLACK, width=1.3, fill=WHITE)
_LABEL = Style(fill=BLACK)


def render(model: GraphSpec, canvas: Canvas) -> Layout:
    x0, x1 = model.x_range
    y0, y1 = model.y_range

    def sx(x: float) -> float:
        return (x - x0) / (x1 - x0) * PLOT_WIDTH

    def sy(y: float) -> float:
        return PLOT_HEIGHT - (y - y0) / (y1 - y0) * PLOT_HEIGHT

    x_ticks, x_fine = axis_divisions(x0, x1, model.x_step, model.x_label_step, _MAX_LABELS_X)
    y_ticks, y_fine = axis_divisions(y0, y1, model.y_step, model.y_label_step, _MAX_LABELS_Y)

    if model.grid != "none":
        x_minor, x_major = _grid_values(x_ticks, x_fine, model.grid)
        y_minor, y_major = _grid_values(y_ticks, y_fine, model.grid)
        # Thin lines first, so the numbered divisions lie on top of them.
        for x in x_minor:
            canvas.add(Line(Pt(sx(x), 0), Pt(sx(x), PLOT_HEIGHT), GRID_FINE))
        for y in y_minor:
            canvas.add(Line(Pt(0, sy(y)), Pt(PLOT_WIDTH, sy(y)), GRID_FINE))
        for x in x_major:
            canvas.add(Line(Pt(sx(x), 0), Pt(sx(x), PLOT_HEIGHT), GRID))
        for y in y_major:
            canvas.add(Line(Pt(0, sy(y)), Pt(PLOT_WIDTH, sy(y)), GRID))

    canvas.extend(_axes(model))
    canvas.extend(_ticks_and_numbers(x_ticks, y_ticks))

    for index, series in enumerate(model.series):
        canvas.extend(_series_nodes(model, series, index, sx, sy))

    if any(series.label for series in model.series):
        canvas.extend(_legend(model, PLOT_HEIGHT + 26))
    return Layout(padding=2.0)


def axis_divisions(
    low: float,
    high: float,
    step: float | None,
    label_step: float | None,
    max_labels: int,
) -> tuple[tuple[Tick, ...], list[float]]:
    """Where one axis is divided, and which divisions carry a number.

    Three cases, and the author picks how far into them to go:

    * nothing pinned — the renderer chooses a round division and numbers all
      of them, as it always has;
    * only the division pinned — the numbers are thinned off it, densest that
      still reads;
    * both pinned — the author is obeyed, the model having checked that the
      numbers land on divisions.

    The second value is the extra sub-division a fine grid needs when every
    division is numbered: with no unnumbered division to rule, "a line inside
    the cell" has to be invented, and graph paper invents it by fifths.
    """
    if step is not None:
        values = division_values(low, high, step)
        every = (
            round(label_step / step)
            if label_step is not None
            else label_every(step, len(values) - 1, max_labels)
        )
    else:
        # Without a division of their own, the numbers are the divisions.
        values = division_values(low, high, label_step) if label_step else nice_ticks(low, high)
        every = 1
    ticks = ticks_at(values, low, high, label_every=every)
    return ticks, subdivisions(values, low, high) if every == 1 else []


def _grid_values(
    ticks: Sequence[Tick], fine: Sequence[float], grid: str
) -> tuple[list[float], list[float]]:
    """Values ruled thinly and values ruled heavily, for one axis.

    A numbered division is ruled whenever there is a grid at all — the value
    is read off that line. Divisions between numbers are ruled only on a fine
    grid, together with the invented sub-divisions.
    """
    major = [tick.value for tick in ticks if tick.labeled]
    if grid != "fine":
        return [], major
    return [tick.value for tick in ticks if not tick.labeled] + list(fine), major


def _axes(model: GraphSpec) -> list[Node]:
    """Both axes, each running past the last division into an arrow, and the
    quantity each measures named in line with its own numbers.

    The captions used to stand inside the plot, where a bar or a rising line
    ran straight through them. Outside they extend the frame instead: the row
    of numbers under the x axis continues into «t, с», the column beside the y
    axis into «υ, м/с», and the plot area is left to the data.
    """
    origin = Pt(0, PLOT_HEIGHT)
    x_tip = Pt(PLOT_WIDTH + _OVERSHOOT_X, PLOT_HEIGHT)
    y_tip = Pt(0, -_OVERSHOOT_Y)
    return [
        *arrow(origin, x_tip, HEAVY, _AXIS_HEAD),
        *arrow(origin, y_tip, HEAVY, _AXIS_HEAD),
        Text(
            Pt(x_tip.x + _CAPTION_GAP, PLOT_HEIGHT + _LABEL_DISTANCE_X),
            model.x_label,
            _AXIS_LABEL_SIZE,
            "start",
            _LABEL,
        ),
        Text(
            # Level with the tip, like a number is level with its tick.
            Pt(-_LABEL_DISTANCE_Y, y_tip.y + _LABEL_SHIFT_Y),
            model.y_label,
            _AXIS_LABEL_SIZE,
            "end",
            _LABEL,
        ),
    ]


def _ticks_and_numbers(x_ticks: Sequence[Tick], y_ticks: Sequence[Tick]) -> list[Node]:
    """Ticks on both axes with their numbers, drawn outwards from the corner.

    Both axes start at the origin so that a tick's fraction runs the way its
    values do: rightwards on X, upwards on Y.
    """
    origin = Pt(0, PLOT_HEIGHT)
    nodes = scale_marks(
        LinearAxis(origin, Pt(PLOT_WIDTH, PLOT_HEIGHT), Pt(0, 1)),
        x_ticks,
        major_length=_TICK_MAJOR,
        minor_length=_TICK_MINOR,
        label_distance=_LABEL_DISTANCE_X,
        label_size=_TICK_LABEL_SIZE,
        formatter=num,
    )
    nodes.extend(
        scale_marks(
            LinearAxis(origin, Pt(0, 0), Pt(-1, 0)),
            y_ticks,
            major_length=_TICK_MAJOR,
            minor_length=_TICK_MINOR,
            label_distance=_LABEL_DISTANCE_Y,
            label_anchor="end",
            label_shift=_LABEL_SHIFT_Y,
            label_size=_TICK_LABEL_SIZE,
            formatter=num,
        )
    )
    return nodes


def _series_nodes(
    model: GraphSpec,
    series: SeriesSpec,
    index: int,
    sx: Callable[[float], float],
    sy: Callable[[float], float],
) -> list[Node]:
    points = [Pt(sx(x), sy(y)) for x, y in series.points]
    dash = DASH[series.style]

    if model.chart_type == "bar":
        width = PLOT_WIDTH / max(len(points), 1) * 0.5
        return [
            Rect(Pt(p.x - width / 2, p.y), width, PLOT_HEIGHT - p.y, _BAR) for p in points
        ]
    if model.chart_type == "scatter":
        shape = MARKER_SHAPES[index % len(MARKER_SHAPES)]
        return [node for p in points for node in marker(shape, p)]
    if len(points) == 1:
        # A one-point line series (a given point in a `plot` question): a path
        # with a single move command draws nothing, so draw the node itself.
        return [Circle(points[0], 3, Style(fill=BLACK))]
    path = PathBuilder().move(points[0]).lines(points[1:])
    return [path.build(_SERIES_LINE.with_(dash=dash))]


def marker(shape: str, at: Pt) -> list[Node]:
    """One data point marker — also used as the legend sample, so the legend
    shows the mark a scatter series actually carries."""
    if shape == "circle":
        return [Circle(at, 3, Style(fill=BLACK))]
    if shape == "cross":
        arm = Style(stroke=BLACK, width=1.3)
        return [
            Line(at.shifted(-3, -3), at.shifted(3, 3), arm),
            Line(at.shifted(-3, 3), at.shifted(3, -3), arm),
        ]
    return [
        Polyline(
            (at.shifted(0, -4), at.shifted(-4, 3), at.shifted(4, 3)),
            Style(fill=BLACK),
            closed=True,
        )
    ]


def _legend(model: GraphSpec, baseline: float) -> list[Node]:
    """Series labels on one centred line, each with the mark that identifies
    its series on the plot."""
    labelled = [(i, s) for i, s in enumerate(model.series) if s.label]
    gap, sample_width = 10.0, 16.0
    widths = [
        sample_width + text_width(series.label or "", _LEGEND_SIZE) for _, series in labelled
    ]
    total = sum(widths) + gap * (len(labelled) - 1)
    x = (PLOT_WIDTH - total) / 2
    nodes: list[Node] = []
    for (index, series), width in zip(labelled, widths):
        sample_y = baseline - 2.5
        nodes.extend(_legend_sample(model, series, index, x, sample_y))
        nodes.append(
            Text(Pt(x + sample_width, baseline), series.label or "", _LEGEND_SIZE, "start", _LABEL)
        )
        x += width + gap
    return nodes


def _legend_sample(
    model: GraphSpec, series: SeriesSpec, index: int, x: float, y: float
) -> Sequence[Node]:
    if model.chart_type == "scatter":
        return marker(MARKER_SHAPES[index % len(MARKER_SHAPES)], Pt(x + 6.5, y))
    if model.chart_type == "bar":
        return [Rect(Pt(x + 2, y - 4), 8, 8, _BAR)]
    return [
        Line(Pt(x, y), Pt(x + 13, y), _SERIES_LINE.with_(dash=DASH[series.style])),
    ]
