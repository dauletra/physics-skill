from components.base import Component
from visuals import build_chart_svg


class GraphComponent(Component):
    """График — тонкая обёртка над `build_chart_svg` (scripts/visuals.py).
    `series` опционально — без него рисуются пустые подписанные оси (для
    "постройте график по данным осям" у ученика)."""

    def __init__(self, x_label, y_label, x_range, y_range, series=None, chart_type="line"):
        self.x_label = x_label
        self.y_label = y_label
        self.x_range = x_range
        self.y_range = y_range
        self.series = series or []
        self.chart_type = chart_type

    def render(self) -> str:
        return build_chart_svg(
            {
                "x_label": self.x_label,
                "y_label": self.y_label,
                "x_range": self.x_range,
                "y_range": self.y_range,
                "series": self.series,
                "chart_type": self.chart_type,
            }
        )

    @classmethod
    def from_dict(cls, data: dict) -> "GraphComponent":
        return cls(
            x_label=data.get("x_label", ""),
            y_label=data.get("y_label", ""),
            x_range=data["x_range"],
            y_range=data["y_range"],
            series=data.get("series"),
            chart_type=data.get("chart_type", "line"),
        )
