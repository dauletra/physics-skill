"""Drawing a graph: grid, axes, series, legend.

The plot area is a fixed rectangle so that graphs on one page share a shape;
everything else — tick labels, axis captions, the legend — extends the frame
around it, and the canvas measures the result. Long y-axis numbers therefore
widen the picture instead of being clipped.

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
from physics_svg.elements import nice_ticks, subdivisions
from physics_svg.visuals.graph.model import GraphSpec, SeriesSpec
from physics_svg.visuals.registry import Layout

#: Plot rectangle in user units. Calibrated for a picture about 330 px wide
#: on screen, which is where the font sizes below read comfortably.
PLOT_WIDTH = 174.0
PLOT_HEIGHT = 92.0

_TICK_LABEL_SIZE = 9.0
_AXIS_LABEL_SIZE = 10.0
_LEGEND_SIZE = 7.0

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

    x_ticks, y_ticks = nice_ticks(x0, x1), nice_ticks(y0, y1)

    if model.grid == "fine":
        # Drawn first so the numbered divisions lie on top of it.
        for x in subdivisions(x_ticks, x0, x1):
            canvas.add(Line(Pt(sx(x), 0), Pt(sx(x), PLOT_HEIGHT), GRID_FINE))
        for y in subdivisions(y_ticks, y0, y1):
            canvas.add(Line(Pt(0, sy(y)), Pt(PLOT_WIDTH, sy(y)), GRID_FINE))

    for x in x_ticks:
        canvas.add(Line(Pt(sx(x), 0), Pt(sx(x), PLOT_HEIGHT), GRID))
        canvas.add(
            Text(Pt(sx(x), PLOT_HEIGHT + 12), num(x), _TICK_LABEL_SIZE, "middle", _LABEL)
        )
    for y in y_ticks:
        canvas.add(Line(Pt(0, sy(y)), Pt(PLOT_WIDTH, sy(y)), GRID))
        canvas.add(Text(Pt(-6, sy(y) + 3), num(y), _TICK_LABEL_SIZE, "end", _LABEL))

    canvas.add(
        Line(Pt(0, PLOT_HEIGHT), Pt(PLOT_WIDTH, PLOT_HEIGHT), HEAVY),
        Line(Pt(0, 0), Pt(0, PLOT_HEIGHT), HEAVY),
        # Axis captions sit inside the plot, at the far end of their axis —
        # the placement school textbooks use.
        Text(Pt(PLOT_WIDTH, PLOT_HEIGHT - 6), model.x_label, _AXIS_LABEL_SIZE, "end", _LABEL),
        Text(Pt(4, 10), model.y_label, _AXIS_LABEL_SIZE, "start", _LABEL),
    )

    for index, series in enumerate(model.series):
        canvas.extend(_series_nodes(model, series, index, sx, sy))

    if any(series.label for series in model.series):
        canvas.extend(_legend(model, PLOT_HEIGHT + 26))
    return Layout(padding=2.0)


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
