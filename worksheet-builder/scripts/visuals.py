"""Генерация SVG-графиков (`chart_spec`) и библиотека сниппетов-иллюстраций
(`svg_snippet`), используемых форматом компонента `visual` (см. components.py)."""
import math

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


# --- Библиотека SVG-сниппетов для типовых иллюстраций ----------------------

def _snippet_inclined_plane(params):
    angle = params.get("angle", 30)
    mass_label = esc(params.get("mass_label", "m"))

    rad = math.radians(angle)
    base_len = 220
    height = base_len * math.tan(rad)
    height = min(height, 140)
    ax, ay = 20, 160
    bx, by = ax + base_len, ay
    cx, cy = ax, ay - height
    return (
        '<svg class="visual-svg" viewBox="0 0 260 190" xmlns="http://www.w3.org/2000/svg" '
        'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
        f'<polygon points="{ax},{ay} {bx},{by} {cx},{cy}" fill="none" stroke="#000" stroke-width="1.5"/>'
        f'<rect x="{(ax+bx)/2-14}" y="{(ay+cy)/2-40}" width="26" height="18" '
        f'fill="none" stroke="#000" stroke-width="1.5" '
        f'transform="rotate(-{angle} {(ax+bx)/2} {(ay+cy)/2-31})"/>'
        f'<text x="{(ax+bx)/2+16}" y="{(ay+cy)/2-30}" font-size="11">{mass_label}</text>'
        f'<text x="{ax+30}" y="{ay-8}" font-size="11">{angle}&#176;</text>'
        "</svg>"
    )


def _snippet_simple_circuit(params):
    r_label = esc(params.get("resistor_label", "R"))
    v_label = esc(params.get("source_label", "ε"))
    return (
        '<svg class="visual-svg" viewBox="0 0 220 140" xmlns="http://www.w3.org/2000/svg" '
        'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
        '<rect x="20" y="20" width="180" height="100" fill="none" stroke="#000" stroke-width="1.5"/>'
        '<rect x="85" y="10" width="50" height="20" fill="#fff" stroke="#000" stroke-width="1.5"/>'
        f'<text x="110" y="24" font-size="11" text-anchor="middle">{r_label}</text>'
        '<line x1="20" y1="60" x2="20" y2="80" stroke="#000" stroke-width="2.5"/>'
        '<line x1="14" y1="65" x2="26" y2="65" stroke="#000" stroke-width="1.5"/>'
        f'<text x="30" y="74" font-size="11">{v_label}</text>'
        "</svg>"
    )


SVG_SNIPPETS = {
    "inclined_plane": _snippet_inclined_plane,
    "simple_circuit": _snippet_simple_circuit,
}


def _resolve_svg(task, snippet_key, raw_key):
    if snippet_key in task:
        name = task[snippet_key]["name"]
        params = task[snippet_key].get("params", {})
        if name not in SVG_SNIPPETS:
            raise ValueError(
                f"Unknown {snippet_key} '{name}'. Available: {list(SVG_SNIPPETS)}. "
                "Use raw_svg instead, or add a generator to SVG_SNIPPETS."
            )
        return SVG_SNIPPETS[name](params)
    if raw_key in task:
        return task[raw_key]
    return None
