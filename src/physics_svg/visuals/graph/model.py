"""A plotted graph with axes.

Data, never pixels: the author states what is measured and over what range,
and the renderer decides gridlines, tick spacing and layout.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.schema import Invalid, Number, field, spec

Point = tuple[Number, Number]
ChartType = Literal["line", "bar", "scatter"]

#: Gridline density, as a ladder: `none` leaves the axes with their ticks
#: alone, `ticks` rules the numbered divisions — values are read off them —
#: and `fine` rules every division, for taking a reading between numbers or
#: plotting a point. Ticks on the axes are drawn either way. Full graph paper
#: is the `paper` type, not a fourth value here.
Grid = Literal["none", "ticks", "fine"]

#: Plot rectangle in user units. Calibrated for a picture about 330 px wide
#: on screen, which is where the tick font size reads comfortably. It lives
#: with the model because the model has to judge whether a pinned step still
#: fits — the renderer draws in the same rectangle.
PLOT_WIDTH = 174.0
PLOT_HEIGHT = 92.0

#: Closest two marks may sit and still read as two, in user units: ticks are
#: short strokes and tolerate crowding, numbers do not. On X the numbers
#: stand side by side and need room for their digits; on Y they only have to
#: clear each other's line.
MIN_TICK_GAP = 2.0
MIN_LABEL_GAP_X = 14.0
MIN_LABEL_GAP_Y = 9.0

#: Tolerance for "is this value a whole multiple of that one" on data that
#: arrived as JSON floats.
_EPS = 1e-6


@spec
class SeriesSpec:
    """Одна серия точек."""

    points: list[Point] = field(min_items=1, doc="Точки серии: [[x, y], …]")
    label: Optional[str] = field(default=None, doc="Подпись в легенде")
    style: Literal["solid", "dashed", "dotted"] = "solid"


@spec
class GraphAxes:
    """The plane a graph is drawn on: what is measured, over what range, how
    densely ruled.

    A field group, not a block — it has no `type`, so it is never a member of
    a union and never parsed on its own. It exists because two blocks are drawn
    on the same plane: the `graph` component and the `plot` question, whose axes
    are given and whose curve is the answer. One declaration means the two
    cannot drift: a new visual field here reaches both, and `plot` cannot
    quietly lack it.

    Declared with `@spec` rather than a bare dataclass so that its fields are
    the same kind of thing as everywhere else — constraints, `doc`, frozen.
    """

    x_label: str = field(doc="Подпись оси X, обычно с единицей: «t, с»")
    y_label: str = field(doc="Подпись оси Y, обычно с единицей: «υ, м/с»")
    x_range: tuple[Number, Number] = field(doc="Диапазон оси X: [min, max]")
    y_range: tuple[Number, Number] = field(doc="Диапазон оси Y: [min, max]")
    x_step: Optional[Number] = field(
        default=None,
        gt=0,
        doc="Цена деления оси X — шаг засечек; не задан, деления выбирает рендерер",
    )
    x_label_step: Optional[Number] = field(
        default=None,
        gt=0,
        doc="Шаг подписанных засечек оси X; кратен 'x_step'",
    )
    y_step: Optional[Number] = field(
        default=None,
        gt=0,
        doc="Цена деления оси Y — шаг засечек; не задан, деления выбирает рендерер",
    )
    y_label_step: Optional[Number] = field(
        default=None,
        gt=0,
        doc="Шаг подписанных засечек оси Y; кратен 'y_step'",
    )

    def check_axes(self) -> None:
        check_range("x_range", self.x_range)
        check_range("y_range", self.y_range)
        check_divisions(
            "x", self.x_range, self.x_step, self.x_label_step, PLOT_WIDTH, MIN_LABEL_GAP_X
        )
        check_divisions(
            "y", self.y_range, self.y_step, self.y_label_step, PLOT_HEIGHT, MIN_LABEL_GAP_Y
        )


@spec
class GraphSpec(GraphAxes):
    """График с осями."""

    type: Literal["graph"]
    id: Optional[str] = None
    chart_type: ChartType = "line"
    grid: Grid = "ticks"
    series: list[SeriesSpec] = field(
        default_factory=list, doc="Серии; пустой список — только оси и сетка"
    )

    def check(self) -> None:
        self.check_axes()
        if self.chart_type == "bar":
            check_bar(self.y_range, len(self.series), "series")


def check_range(name: str, value: tuple[float, float]) -> None:
    low, high = value
    if not low < high:
        raise Invalid(
            f"диапазон должен быть [min, max] с min < max, получено [{low}, {high}]",
            field=name,
        )


def check_divisions(
    axis: str,
    value_range: tuple[float, float],
    step: float | None,
    label_step: float | None,
    length: float,
    min_label_gap: float,
) -> None:
    """Invariants of a pinned scale: divisions land on the axis, and the marks
    stay far enough apart to be read.

    Nothing is checked when the author pins nothing — the renderer's own
    choice is round and sparse by construction.
    """
    low, high = value_range
    span = high - low
    if step is not None:
        if not _is_multiple(span, step):
            raise Invalid(
                f"цена деления {step} должна укладываться в диапазон [{low}, {high}] "
                f"нацело: (max - min) / step = {span / step}",
                field=f"{axis}_step",
            )
        limit = int(length // MIN_TICK_GAP)
        if round(span / step) > limit:
            raise Invalid(
                f"цена деления {step} даёт {round(span / step)} делений по оси "
                f"{axis.upper()} — засечки сольются, читаемо не больше {limit}; "
                "возьми шаг крупнее",
                field=f"{axis}_step",
            )
    if label_step is None:
        return
    # Multiplicity first: it is the more specific mistake, and a label step
    # that misses the ticks usually misses the far end of the axis too.
    if step is not None and not _is_multiple(label_step, step):
        raise Invalid(
            f"шаг подписей {label_step} должен быть кратен цене деления {step}: "
            "подписи стоят на засечках",
            field=f"{axis}_label_step",
        )
    if not _is_multiple(span, label_step):
        raise Invalid(
            f"шаг подписей {label_step} должен укладываться в диапазон [{low}, {high}] "
            f"нацело: (max - min) / label_step = {span / label_step}",
            field=f"{axis}_label_step",
        )
    labels = round(span / label_step) + 1
    limit = int(length // min_label_gap) + 1
    if labels > limit:
        raise Invalid(
            f"шаг подписей {label_step} даёт {labels} подписей по оси {axis.upper()} — "
            f"они налезут друг на друга, читаемо не больше {limit}; возьми шаг крупнее",
            field=f"{axis}_label_step",
        )


def _is_multiple(value: float, unit: float) -> bool:
    ratio = value / unit
    return round(ratio) >= 1 and abs(ratio - round(ratio)) <= _EPS * max(round(ratio), 1)


def check_bar(y_range: tuple[float, float], series_count: int, field_name: str) -> None:
    """Invariants a bar chart cannot be honest without."""
    if series_count > 1:
        # Bars of two series would be drawn on top of each other.
        raise Invalid(
            f"столбчатый график поддерживает только одну серию, получено {series_count}",
            field=field_name,
        )
    if y_range[0] != 0:
        # A bar that does not grow from zero lies about the ratio of heights.
        raise Invalid(
            "у столбчатого графика ось Y должна начинаться с нуля, "
            f"получено [{y_range[0]}, {y_range[1]}]",
            field="y_range",
        )
