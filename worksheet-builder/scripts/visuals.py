"""Генерация SVG-графиков (`chart_spec`), используемых компонентом `graph`
(`components/graph.py`) и `GraphQuestion` (`questions/graph_question.py`).

Иллюстрации/схемы (`svg_snippet`/`raw_svg`) намеренно вне scope v2 — см.
"Явно вне scope" в references/task-schema.md."""

from render_helpers import esc

DASH_PATTERNS = {"solid": None, "dashed": "8,4", "dotted": "1,3"}
MARKER_SHAPES = ["circle", "cross", "triangle"]


def _linspace(a, b, n):
    if n <= 1:
        return [a]
    step = (b - a) / (n - 1)
    return [a + step * i for i in range(n)]


def _fmt_num(n):
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def build_chart_svg(spec):
    # Рассчитано под боковую колонку шириной ~36% (task-visual), а не под всю
    # ширину страницы — единицы viewBox подобраны так, чтобы font-size/
    # stroke-width ниже давали читаемый физический размер после масштабирования
    # под реальную ширину этой колонки.
    width, height = 220, 124
    margin = {"left": 36, "right": 10, "top": 10, "bottom": 22}
    plot_w = width - margin["left"] - margin["right"]
    plot_h = height - margin["top"] - margin["bottom"]
    x0, x1 = spec["x_range"]
    y0, y1 = spec["y_range"]

    def sx(x):
        return margin["left"] + (x - x0) / (x1 - x0) * plot_w

    def sy(y):
        return margin["top"] + plot_h - (y - y0) / (y1 - y0) * plot_h

    parts = [
        f'<svg class="visual-svg" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
        f'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
    ]

    # Сетка + подписи делений
    for gx in _linspace(x0, x1, 6):
        px = sx(gx)
        parts.append(
            f'<line x1="{px:.1f}" y1="{margin["top"]}" x2="{px:.1f}" '
            f'y2="{margin["top"] + plot_h}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{px:.1f}" y="{margin["top"] + plot_h + 12}" font-size="9" '
            f'text-anchor="middle">{_fmt_num(gx)}</text>'
        )
    for gy in _linspace(y0, y1, 6):
        py = sy(gy)
        parts.append(
            f'<line x1="{margin["left"]}" y1="{py:.1f}" '
            f'x2="{margin["left"] + plot_w}" y2="{py:.1f}" stroke="#ccc" stroke-width="0.6"/>'
        )
        parts.append(
            f'<text x="{margin["left"] - 6}" y="{py + 3:.1f}" font-size="9" '
            f'text-anchor="end">{_fmt_num(gy)}</text>'
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
        f'font-size="10" text-anchor="end">{esc(spec.get("x_label", ""))}</text>'
    )
    parts.append(
        f'<text x="{margin["left"] + 4}" y="{margin["top"] + 10}" '
        f'font-size="10" text-anchor="start">{esc(spec.get("y_label", ""))}</text>'
    )

    chart_type = spec.get("chart_type", "line")
    series = spec.get("series", [])
    legend_items = []
    for i, s in enumerate(series):
        points = s.get("points", [])
        style = s.get("style", "solid")
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
                px, py = sx(x), sy(y)
                if shape == "circle":
                    parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#000"/>')
                elif shape == "cross":
                    parts.append(
                        f'<line x1="{px-3:.1f}" y1="{py-3:.1f}" x2="{px+3:.1f}" y2="{py+3:.1f}" stroke="#000" stroke-width="1.3"/>'
                        f'<line x1="{px-3:.1f}" y1="{py+3:.1f}" x2="{px+3:.1f}" y2="{py-3:.1f}" stroke="#000" stroke-width="1.3"/>'
                    )
                else:
                    parts.append(
                        f'<polygon points="{px:.1f},{py-4:.1f} {px-4:.1f},{py+3:.1f} {px+4:.1f},{py+3:.1f}" fill="#000"/>'
                    )
        else:  # линия
            path = " ".join(
                f'{"M" if idx == 0 else "L"}{sx(x):.1f},{sy(y):.1f}'
                for idx, (x, y) in enumerate(points)
            )
            parts.append(f'<path d="{path}" fill="none" stroke="#000" stroke-width="2"{dash_attr}/>')
        if s.get("label"):
            legend_items.append((s["label"], style, i))

    parts.append("</svg>")
    svg = "".join(parts)

    legend_html = ""
    if legend_items:
        chips = []
        for label, style, i in legend_items:
            dash = DASH_PATTERNS.get(style)
            sample = (
                f'<svg width="20" height="10"><line x1="0" y1="5" x2="20" y2="5" '
                f'stroke="#000" stroke-width="2"'
                + (f' stroke-dasharray="{dash}"' if dash else "")
                + "/></svg>"
            )
            chips.append(f'<span>{sample} {esc(label)}</span>')
        legend_html = f'<div class="chart-legend">{"".join(chips)}</div>'

    return f'<div class="chart-wrap">{svg}{legend_html}</div>'
