"""Plot the graph — axes are given, the curve is the answer.

The payload is literally the `graph` component's plane (`GraphAxes`, shared
declaration) plus two sets of series: `given` (already drawn for the student)
and `answer` (drawn in the answers section). Both renderers build a real
`GraphSpec`, so a plotting question and an illustration can never drift apart
visually.

Why the drawing surface lives inside the question here, when a place to write
is normally a neighbouring component: the axes are not blank space, they fix
the scale the student must plot in, and the answer is geometry that means
nothing outside them. See принцип 3 in docs/schema-design-principles.md.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Block
from physics_svg.document.questions.registry import register
from physics_svg.schema import field, spec
from physics_svg.visuals import build_svg
from physics_svg.visuals.graph.model import (
    ChartType,
    GraphAxes,
    GraphSpec,
    Grid,
    SeriesSpec,
    check_bar,
)


@spec
class PlotSpec(GraphAxes):
    """Построение графика по данным."""

    type: Literal["plot"]
    answer: list[SeriesSpec] = field(min_items=1, doc="Правильные серии — в секцию «Ответы»")
    id: Optional[str] = None
    explanation: Optional[str] = None
    chart_type: ChartType = "line"
    grid: Grid = "ticks"
    given: Optional[list[SeriesSpec]] = field(
        default=None, doc="Серии, уже нарисованные ученику на осях"
    )

    def check(self) -> None:
        self.check_axes()
        if self.chart_type == "bar":
            check_bar(self.y_range, max(len(self.answer), len(self.given or [])), "answer")

    def as_graph(self, series: list[SeriesSpec]) -> GraphSpec:
        return GraphSpec(
            type="graph",
            x_label=self.x_label,
            y_label=self.y_label,
            x_range=self.x_range,
            y_range=self.y_range,
            x_step=self.x_step,
            x_label_step=self.x_label_step,
            y_step=self.y_step,
            y_label_step=self.y_label_step,
            chart_type=self.chart_type,
            grid=self.grid,
            series=series,
        )


def body(model: PlotSpec) -> str:
    return build_svg(model.as_graph(model.given or []), scope=f"plot-{model.id or 'q'}")


def answer(model: PlotSpec) -> Answer:
    """The correct graph, on the same axes as the body.

    A `Block`, not a compact line: the answers section gives a drawing its own
    room instead of squeezing it into the slot that holds «б».
    """
    return Block(build_svg(model.as_graph(model.answer), scope=f"plot-{model.id or 'q'}-a"))


register(
    tag="plot",
    title="Построение графика",
    model=PlotSpec,
    body=body,
    answer=answer,
    order=90,
    module=__name__,
)
