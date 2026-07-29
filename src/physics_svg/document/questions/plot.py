"""Plot the graph — axes are given, the curve is the answer.

The payload is the `graph` component's own fields plus two sets of series:
`given` (already drawn for the student) and `answer` (drawn in the answers
section). Both renderers build a real `GraphSpec`, so a plotting question and
an illustration can never drift apart visually.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.questions.registry import register
from physics_svg.schema import Number, field, spec
from physics_svg.visuals import build_svg
from physics_svg.visuals.graph.model import (
    ChartType,
    GraphSpec,
    Grid,
    SeriesSpec,
    check_bar,
    check_range,
)


@spec
class PlotSpec:
    """Построение графика по данным."""

    type: Literal["plot"]
    x_label: str = field(doc="Подпись оси X")
    y_label: str = field(doc="Подпись оси Y")
    x_range: tuple[Number, Number] = field(doc="Диапазон оси X: [min, max]")
    y_range: tuple[Number, Number] = field(doc="Диапазон оси Y: [min, max]")
    answer: list[SeriesSpec] = field(min_items=1, doc="Правильные серии — в секцию «Ответы»")
    id: Optional[str] = None
    explanation: Optional[str] = None
    chart_type: ChartType = "line"
    grid: Grid = "ticks"
    given: Optional[list[SeriesSpec]] = field(
        default=None, doc="Серии, уже нарисованные ученику на осях"
    )

    def check(self) -> None:
        check_range("x_range", self.x_range)
        check_range("y_range", self.y_range)
        if self.chart_type == "bar":
            check_bar(self.y_range, max(len(self.answer), len(self.given or [])), "answer")

    def as_graph(self, series: list[SeriesSpec]) -> GraphSpec:
        return GraphSpec(
            type="graph",
            x_label=self.x_label,
            y_label=self.y_label,
            x_range=self.x_range,
            y_range=self.y_range,
            chart_type=self.chart_type,
            grid=self.grid,
            series=series,
        )


def body(model: PlotSpec) -> str:
    return build_svg(model.as_graph(model.given or []), scope=f"plot-{model.id or 'q'}")


def answer(model: PlotSpec) -> str:
    """The correct graph, on the same axes as the body."""
    return build_svg(model.as_graph(model.answer), scope=f"plot-{model.id or 'q'}-a")


register(
    tag="plot", title="Построение графика", model=PlotSpec, body=body, answer=answer,
    module=__name__,
)
