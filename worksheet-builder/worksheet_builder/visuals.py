"""Генерация SVG-графиков (`build_chart_svg`), используемых рендером
компонента `graph` (components.py) и вопроса `plot` (questions.py).

Иллюстрации/схемы (`svg_snippet`/`raw_svg`) намеренно вне scope — см.
"Явно вне scope" в references/document-schema.md."""

import math
from collections.abc import Sequence

from worksheet_builder.models import SeriesModel
from worksheet_builder.render_helpers import esc, fmt_num, svg_label

DASH_PATTERNS = {"solid": None, "dashed": "8,4", "dotted": "1,3"}
MARKER_SHAPES = ["circle", "cross", "triangle"]


def _marker_svg(shape: str, cx: float, cy: float) -> str:
    """Один маркер точки данных — используется и на самом графике (scatter),
    и как образец в легенде, чтобы легенда показывала реальный отличительный
    признак серии, а не линию, которой на scatter-графике нет."""
    if shape == "circle":
        return f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="#000"/>'
    if shape == "cross":
        return (
            f'<line x1="{cx-3:.1f}" y1="{cy-3:.1f}" x2="{cx+3:.1f}" y2="{cy+3:.1f}" stroke="#000" stroke-width="1.3"/>'
            f'<line x1="{cx-3:.1f}" y1="{cy+3:.1f}" x2="{cx+3:.1f}" y2="{cy-3:.1f}" stroke="#000" stroke-width="1.3"/>'
        )
    return f'<polygon points="{cx:.1f},{cy-4:.1f} {cx-4:.1f},{cy+3:.1f} {cx+4:.1f},{cy+3:.1f}" fill="#000"/>'


def _tick_positions(lo: float, hi: float, max_ticks: int = 9) -> list[float]:
    """Круглые деления оси: шаг — 1/2/5 × 10ⁿ, берётся самый плотный вариант,
    дающий не больше max_ticks делений внутри [lo, hi]. Ученик считывает
    значения по сетке — дробный «шаг = диапазон/5» здесь был бы дефектом,
    а не косметикой."""
    span = hi - lo
    base_exp = math.floor(math.log10(span)) - 2
    for exp in range(base_exp, base_exp + 5):
        for mantissa in (1, 2, 5):
            step = mantissa * 10 ** exp
            n0 = math.ceil(lo / step - 1e-9)
            n1 = math.floor(hi / step + 1e-9)
            if 2 <= n1 - n0 + 1 <= max_ticks:
                return [n * step for n in range(n0, n1 + 1)]
    return [lo, hi]


def build_chart_svg(
    x_label: str,
    y_label: str,
    x_range: tuple[float, float],
    y_range: tuple[float, float],
    series: Sequence[SeriesModel] = (),
    chart_type: str = "line",
) -> str:
    """`series` — список `SeriesModel` (models.py): единственное представление
    серии, отдельной dict-формы нет.

    Рассчитано под целевую экранную ширину 330px (max-width у svg.visual-svg
    в BASE_CSS), а не под всю ширину колонки текста — единицы viewBox
    подобраны так, чтобы font-size/stroke-width ниже давали читаемый размер
    после масштабирования под эту ширину. Если меняешь max-width в CSS,
    перепроверь калибровку рендером."""
    width, height = 220, 124
    margin = {"left": 36, "right": 10, "top": 10, "bottom": 22}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    x0, x1 = x_range
    y0, y1 = y_range

    def sx(x: float) -> float:
        return margin["left"] + (x - x0) / (x1 - x0) * plot_w

    def sy(y: float) -> float:
        return margin["top"] + plot_h - (y - y0) / (y1 - y0) * plot_h

    parts = [
        f'<svg class="visual-svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
    ]

    # Сетка + подписи делений
    for gx in _tick_positions(x0, x1):
        px = sx(gx)
        parts.append(
            f'<line x1="{px:.1f}" y1="{margin["top"]}" x2="{px:.1f}" '
            f'y2="{margin["top"] + plot_h}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{margin["top"] + plot_h + 12}" font-size="9" '
            f'text-anchor="middle">{fmt_num(gx)}</text>'
        )
    for gy in _tick_positions(y0, y1):
        py = sy(gy)
        parts.append(
            f'<line x1="{margin["left"]}" y1="{py:.1f}" '
            f'x2="{margin["left"] + plot_w}" y2="{py:.1f}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{margin["left"] - 6}" y="{py + 3:.1f}" font-size="9" '
            f'text-anchor="end">{fmt_num(gy)}</text>'
        )

    # Оси
    parts.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"] + plot_h}" '
        f'x2="{margin["left"] + plot_w}" y2="{margin["top"] + plot_h}" '
        'stroke="#000" stroke-width="1.5"/>'
    )
    parts.append(
        f'<line x1="{margin["left"]}" y1="{margin["top"]}" '
        f'x2="{margin["left"]}" y2="{margin["top"] + plot_h}" stroke="#000" stroke-width="1.5"/>'
    )
    parts.append(
        f'<text x="{margin["left"] + plot_w}" y="{margin["top"] + plot_h - 6}" '
        f'font-size="10" text-anchor="end">{svg_label(x_label)}</text>'
    )
    parts.append(
        f'<text x="{margin["left"] + 4}" y="{margin["top"] + 10}" '
        f'font-size="10" text-anchor="start">{svg_label(y_label)}</text>'
    )

    legend_items = []
    for i, s in enumerate(series):
        points = s.points
        style = s.style
        dash = DASH_PATTERNS.get(style)
        dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
        if chart_type == "bar":
            bar_w = plot_w / max(len(points), 1) * 0.5
            for (x, y) in points:
                bx = sx(x) - bar_w / 2
                by = sy(y)
                bh = margin["top"] + plot_h - by
                parts.append(
                    f'<rect x="{bx:.1f}" y="{by:.1f}" width="{bar_w:.1f}" height="{bh:.1f}" '
                    f'fill="#fff" stroke="#000" stroke-width="1.3"{dash_attr}/>'
                )
        elif chart_type == "scatter":
            shape = MARKER_SHAPES[i % len(MARKER_SHAPES)]
            for (x, y) in points:
                parts.append(_marker_svg(shape, sx(x), sy(y)))
        elif len(points) == 1:
            # Line-серия из одной точки (данная точка в plot.given): path из
            # одной команды M невидим — рисуем узел (см. artifacts/graphs.md).
            x, y = points[0]
            parts.append(f'<circle cx="{sx(x):.1f}" cy="{sy(y):.1f}" r="3" fill="#000"/>')
        else:  # линия
            path = " ".join(
                f'{"M" if idx == 0 else "L"}{sx(x):.1f},{sy(y):.1f}'
                for idx, (x, y) in enumerate(points)
            )
            parts.append(f'<path d="{path}" fill="none" stroke="#000" stroke-width="2"{dash_attr}/>')
        if s.label:
            legend_items.append((s.label, style, i))

    parts.append("</svg>")
    svg = "".join(parts)

    legend_html = ""
    if legend_items:
        chips = []
        for label, style, i in legend_items:
            if chart_type == "scatter":
                # Серии scatter различаются формой маркера, а не линией —
                # образец в легенде показывает именно маркер.
                shape = MARKER_SHAPES[i % len(MARKER_SHAPES)]
                sample = f'<svg width="20" height="10">{_marker_svg(shape, 10, 5)}</svg>'
            elif chart_type == "bar":
                sample = (
                    '<svg width="20" height="10"><rect x="6" y="1" width="8" height="8" '
                    'fill="#fff" stroke="#000" stroke-width="1.3"/></svg>'
                )
            else:
                dash = DASH_PATTERNS.get(style)
                sample = (
                    '<svg width="20" height="10"><line x1="0" y1="5" x2="20" y2="5" '
                    'stroke="#000" stroke-width="2"'
                    + (f' stroke-dasharray="{dash}"' if dash else "")
                    + "/></svg>"
                )
            chips.append(f'<span>{sample} {esc(label)}</span>')
        legend_html = f'<div class="chart-legend">{"".join(chips)}</div>'

    return f'<div class="chart-wrap">{svg}{legend_html}</div>'
