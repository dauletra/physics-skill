from components.graph import GraphComponent
from questions.base import Question, envelope


class PlotQuestion(Question):
    """Построить график. Оси — та же форма полей, что у компонента `graph`;
    `given` (опционально) — серии, уже данные ученику на осях; `answer` —
    серии правильного ответа (рисуются только в тичер-версии)."""

    type = "plot"

    def __init__(self, x_label, y_label, x_range, y_range, given=None, answer=None, chart_type="line", **kwargs):
        super().__init__(**kwargs)
        self.x_label = x_label
        self.y_label = y_label
        self.x_range = x_range
        self.y_range = y_range
        self.given = given
        self.answer = answer or []
        self.chart_type = chart_type

    def validate(self) -> None:
        if not self.answer:
            raise ValueError("plot: answer series must be non-empty")

    def render_body(self, mode, lang) -> str:
        series = self.answer if mode == "teacher" else (self.given or [])
        return GraphComponent(
            x_label=self.x_label,
            y_label=self.y_label,
            x_range=self.x_range,
            y_range=self.y_range,
            series=series,
            chart_type=self.chart_type,
        ).render()

    @classmethod
    def from_dict(cls, data: dict) -> "PlotQuestion":
        return cls(
            x_label=data.get("x_label", ""),
            y_label=data.get("y_label", ""),
            x_range=data["x_range"],
            y_range=data["y_range"],
            given=data.get("given"),
            answer=data.get("answer"),
            chart_type=data.get("chart_type", "line"),
            **envelope(data),
        )
