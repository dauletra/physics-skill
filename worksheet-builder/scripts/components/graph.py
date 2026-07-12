from components.base import Component
from visuals import build_chart_svg, CHART_TYPES


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
        chart_type = data.get("chart_type", "line")
        # Неизвестный тип падает здесь, а не молча рендерится линией.
        if chart_type not in CHART_TYPES:
            raise ValueError(f"graph: chart_type must be one of {CHART_TYPES}, got {chart_type!r}")
        series = data.get("series") or []
        if chart_type == "bar" and len(series) > 1:
            # Столбики нескольких серий рисовались бы друг поверх друга.
            raise ValueError(f"graph: chart_type 'bar' supports a single series, got {len(series)}")
        return cls(
            x_label=data.get("x_label", ""),
            y_label=data.get("y_label", ""),
            x_range=data["x_range"],
            y_range=data["y_range"],
            series=series,
            chart_type=chart_type,
        )
