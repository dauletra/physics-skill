"""Сборка самодостаточного SVG-файла из одного визуального блока — режим
`--visual` (cli.py): иллюстрация нужна сама по себе (презентация, отдельная
карточка), без рабочего листа вокруг.

Строится поверх `render_component` (components.py): из фрагмента листа
извлекается корневой `<svg class="visual-svg">` — это общий контракт всех
SVG-генераторов (references/artifacts/README.md), поэтому новый генератор
подхватывается здесь без правок. Всё, что в листе делает CSS-оболочка,
переезжает в корень файла: явные width/height (та же калибровка ~1.5px на
единицу viewBox), font-family, белая подложка. Подпись прибора и легенда
графика в листе живут HTML-ом рядом с SVG — здесь они дорисовываются
`<text>`-ами внутрь SVG, потому что файл существует без HTML вообще."""

import re

from worksheet_builder.components import render_component
from worksheet_builder.models import GraphModel, InstrumentModel, VisualModel
from worksheet_builder.render_helpers import fmt_num, svg_label
from worksheet_builder.visuals import DASH_PATTERNS, MARKER_SHAPES, _marker_svg

# Экранная калибровка всех SVG листа (references/artifacts/README.md):
# CSS-ширины подобраны из расчёта ~1.5px на единицу viewBox. Standalone-файл
# живёт без CSS, поэтому масштаб зашивается в width/height корня.
SCALE = 1.5
FONT_STACK = "PT Sans, Segoe UI, Verdana, Arial, sans-serif"

# Корневой тег любого генератора: класс visual-svg + viewBox от нуля.
_VISUAL_SVG_RE = re.compile(
    r'<svg class="visual-svg" viewBox="0 0 (\d+) (\d+)"[^>]*>(.*?)</svg>', re.S
)

# Нижняя строка под рисунком (легенда/подпись): высота добавки к viewBox и
# базовая линия текста, в единицах viewBox.
_FOOTER_H = 14.0
_FOOTER_BASELINE = 10.0
# Оценка ширины текста для центрирования легенды: средний advance PT Sans
# ~0.55em при кегле 7 — точного измерения текста в SVG без клиента нет.
_LEGEND_CHAR_W = 3.8


def _legend_svg(model: GraphModel, w: float, y: float) -> list[str]:
    """Легенда серий одной строкой по центру — SVG-эквивалент `.chart-legend`
    листа: образец отличительного признака серии (линия/маркер/столбик,
    та же логика, что в build_chart_svg) + подпись."""
    labeled = [(i, s) for i, s in enumerate(model.series) if s.label]
    widths = [16 + _LEGEND_CHAR_W * len(s.label or "") for _, s in labeled]
    x = max((w - sum(widths) - 10 * (len(labeled) - 1)) / 2, 2)
    parts: list[str] = []
    for (i, s), item_w in zip(labeled, widths):
        sample_y = y - 2.5
        if model.chart_type == "scatter":
            parts.append(_marker_svg(MARKER_SHAPES[i % len(MARKER_SHAPES)], x + 6.5, sample_y))
        elif model.chart_type == "bar":
            parts.append(
                f'<rect x="{x + 2:.1f}" y="{sample_y - 4:.1f}" width="8" height="8" '
                'fill="#fff" stroke="#000" stroke-width="1.3"/>'
            )
        else:
            dash = DASH_PATTERNS.get(s.style)
            dash_attr = f' stroke-dasharray="{dash}"' if dash else ""
            parts.append(
                f'<line x1="{x:.1f}" y1="{sample_y:.1f}" x2="{x + 13:.1f}" y2="{sample_y:.1f}" '
                f'stroke="#000" stroke-width="2"{dash_attr}/>'
            )
        parts.append(
            f'<text x="{x + 16:.1f}" y="{y:.1f}" font-size="7" text-anchor="start">'
            f"{svg_label(s.label or '')}</text>"
        )
        x += item_w + 10
    return parts


def build_standalone_svg(model: VisualModel, zoom: float = 1.0) -> str:
    """Самодостаточный SVG одного визуального блока (для `--visual`).

    `zoom` — множитель экранного размера (`--scale`): растягивает
    width/height корня при том же viewBox, так что вся геометрия и шрифты
    растут пропорционально — крупная иллюстрация для учебника/слайда.
    Калибровку листа (1.5px/ед.) он не трогает: базовый размер задаёт
    SCALE, zoom применяется поверх."""
    fragment = render_component(model)
    match = _VISUAL_SVG_RE.search(fragment)
    if match is None:
        # Нарушен контракт генераторов (visual-svg + viewBox), это не ошибка
        # авторских данных — валидными данными сюда не попасть.
        raise ValueError(f"component {model.type!r} did not produce a visual-svg block")
    w, h = float(match.group(1)), float(match.group(2))
    inner = match.group(3)

    footer: list[str] = []
    if isinstance(model, GraphModel) and any(s.label for s in model.series):
        footer = _legend_svg(model, w, h + _FOOTER_BASELINE)
    elif isinstance(model, InstrumentModel) and model.caption:
        footer = [
            f'<text x="{w / 2:.1f}" y="{h + _FOOTER_BASELINE:.1f}" font-size="8" '
            f'text-anchor="middle">{svg_label(model.caption)}</text>'
        ]
    total_h = h + (_FOOTER_H if footer else 0)

    px = SCALE * zoom
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{fmt_num(w * px)}" height="{fmt_num(total_h * px)}" '
        f'viewBox="0 0 {fmt_num(w)} {fmt_num(total_h)}" font-family="{FONT_STACK}">'
        f'<rect x="0" y="0" width="{fmt_num(w)}" height="{fmt_num(total_h)}" fill="#fff"/>'
        f'{inner}{"".join(footer)}</svg>'
    )
