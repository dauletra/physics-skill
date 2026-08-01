"""A plotted graph with axes.

Data, never pixels: the author states what is measured and over what range,
and the renderer decides gridlines, tick spacing and layout.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.schema import Invalid, Number, field, spec

Point = tuple[Number, Number]
ChartType = Literal["line", "bar", "scatter"]

#: Gridline density. Lines at the numbered divisions are always there —
#: values are read off them; `fine` adds lines inside a division, for taking
#: a reading between numbers or plotting a point. Full graph paper is the
#: `paper` type, not a third value here.
Grid = Literal["ticks", "fine"]


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

    def check_axes(self) -> None:
        check_range("x_range", self.x_range)
        check_range("y_range", self.y_range)


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
