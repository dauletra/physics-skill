"""Генерация SVG «бумаги» (`build_paper_svg`) для компонента `paper`
(components.py): место, размеченное под работу ученика. Разлиновок пять —
`lines` (линии), `grid` (клетка), `mm` (миллиметровка), `dots` (точки),
`plain` (чистое поле в рамке); новая добавляется строкой в `PaperRuling`
(models.py) и функцией в `_RULING_PAINTERS` — ни CSS, ни standalone,
ни модели трогать не нужно.

Конвенции — references/artifacts/README.md: только ч/б (разлиновка —
вспомогательная сетка, поэтому серая), геометрия в единицах viewBox при
масштабе ~1.5px на единицу. Авторского текста здесь нет вообще — бумага
рисуется по числам, эскейпить нечего.

Две особенности против остальных генераторов листа:

- **`<defs>`/`<pattern>` — здесь можно.** В instruments.py их избегают,
  потому что id в HTML глобальны, а приборов на листе много. Здесь id
  выводится из параметров разлиновки (`paper-grid-12`), поэтому совпадение
  id всегда означает совпадение содержимого: два одинаковых поля делят одно
  определение, разные получают разные id. Без паттерна миллиметровка 12x12
  см — это ~240 линий в HTML на каждое поле.
- **Ширина бывает не задана.** У `lines`/`plain` горизонтальной геометрии
  нет, поэтому без `cols` они тянутся на всю колонку
  (`preserveAspectRatio="none"`): горизонтальную линию растяжение не
  искажает, а высота строки остаётся ровно той, что задана. Чтобы
  анизотропный масштаб не сделал из линии нитку, штрих у них экранный
  (`vector-effect="non-scaling-stroke"`, ширина в px, а не в единицах
  viewBox).
"""

from typing import Callable

from worksheet_builder.models import (
    PAPER_NOMINAL_W,
    PAPER_STEPS,
    PaperModel,
)
from worksheet_builder.render_helpers import fmt_num

# Экранный масштаб листа: 1 единица viewBox = 1.5px (общая калибровка всех
# SVG документа, см. references/artifacts/README.md).
SCREEN_PX = 1.5

# Разлиновка — вспомогательная сетка, а не смысловая линия: серая, чтобы
# написанное поверх читалось лучше самой бумаги (README, «только ч/б»).
_GRID_FINE = "#ddd"
_GRID_MID = "#bbb"
_GRID_MAJOR = "#888"
_FRAME = "#999"


def _frame(w: float, h: float, width: float = 0.7, screen_stroke: bool = False) -> str:
    """Рамка поля. `screen_stroke` — для разлиновок, тянущихся по ширине:
    там масштаб по осям разный, и обычный штрих на вертикальных сторонах
    рамки вышел бы другой толщины, чем на горизонтальных."""
    effect = ' vector-effect="non-scaling-stroke"' if screen_stroke else ""
    return (
        f'<rect x="0" y="0" width="{fmt_num(w)}" height="{fmt_num(h)}" fill="none" '
        f'stroke="{_FRAME}" stroke-width="{fmt_num(width)}"{effect}/>'
    )


def _paint_lines(w: float, h: float) -> str:
    """Линии под запись — штрих на нижней границе каждой строки, как у
    тетрадного листа в линейку. Паттерн здесь не нужен: строк десятки, а не
    сотни, зато явные линии переживают растяжение по ширине."""
    step = PAPER_STEPS["lines"]
    return "".join(
        f'<line x1="0" y1="{fmt_num(step * i)}" x2="{fmt_num(w)}" y2="{fmt_num(step * i)}" '
        'stroke="#000" stroke-width="1" stroke-dasharray="1,3" '
        'vector-effect="non-scaling-stroke"/>'
        for i in range(1, round(h / step) + 1)
    )


def _paint_plain(w: float, h: float) -> str:
    """Чистое поле — только рамка (место под рисунок/чертёж/свободную
    запись)."""
    return _frame(w, h, width=1, screen_stroke=True)


def _paint_grid(w: float, h: float) -> str:
    """Клетка тетрадного листа — один уровень линий."""
    step = PAPER_STEPS["grid"]
    pid = f"paper-grid-{step}"
    return (
        f'<defs><pattern id="{pid}" width="{step}" height="{step}" '
        'patternUnits="userSpaceOnUse">'
        f'<path d="M{step} 0 L0 0 0 {step}" fill="none" stroke="{_GRID_MID}" '
        'stroke-width="0.5"/></pattern></defs>'
        f'<rect x="0" y="0" width="{fmt_num(w)}" height="{fmt_num(h)}" fill="url(#{pid})"/>'
        + _frame(w, h)
    )


def _paint_dots(w: float, h: float) -> str:
    """Точки в узлах решётки — та же клетка, но не перечёркивающая
    построения. Точка ставится в центре ячейки паттерна: у края поля она
    тогда не срезается рамкой."""
    step = PAPER_STEPS["dots"]
    pid = f"paper-dots-{step}"
    half = fmt_num(step / 2)
    return (
        f'<defs><pattern id="{pid}" width="{step}" height="{step}" '
        'patternUnits="userSpaceOnUse">'
        f'<circle cx="{half}" cy="{half}" r="0.8" fill="{_GRID_MID}"/></pattern></defs>'
        f'<rect x="0" y="0" width="{fmt_num(w)}" height="{fmt_num(h)}" fill="url(#{pid})"/>'
        + _frame(w, h)
    )


def _paint_mm(w: float, h: float) -> str:
    """Миллиметровка — три уровня линий настоящей бумаги: тонкая через 1 мм,
    средняя через 5 мм, жирная через 1 см. Собирается вложенными паттернами:
    крупная клетка заливается мелкой, поэтому разметка не зависит от площади
    поля."""
    major = PAPER_STEPS["mm"]
    fine = major / 10
    mid = major / 2
    fine_id, major_id = f"paper-mm-{fmt_num(fine)}", f"paper-mm-{major}"
    return (
        "<defs>"
        f'<pattern id="{fine_id}" width="{fmt_num(fine)}" height="{fmt_num(fine)}" '
        'patternUnits="userSpaceOnUse">'
        f'<path d="M{fmt_num(fine)} 0 L0 0 0 {fmt_num(fine)}" fill="none" '
        f'stroke="{_GRID_FINE}" stroke-width="0.3"/></pattern>'
        f'<pattern id="{major_id}" width="{major}" height="{major}" '
        'patternUnits="userSpaceOnUse">'
        f'<rect width="{major}" height="{major}" fill="url(#{fine_id})"/>'
        f'<path d="M{fmt_num(mid)} 0 L{fmt_num(mid)} {major} M0 {fmt_num(mid)} '
        f'L{major} {fmt_num(mid)}" fill="none" stroke="{_GRID_MID}" stroke-width="0.4"/>'
        f'<path d="M{major} 0 L0 0 0 {major}" fill="none" stroke="{_GRID_MAJOR}" '
        'stroke-width="0.8"/></pattern></defs>'
        f'<rect x="0" y="0" width="{fmt_num(w)}" height="{fmt_num(h)}" fill="url(#{major_id})"/>'
        + _frame(w, h)
    )


_RULING_PAINTERS: dict[str, Callable[[float, float], str]] = {
    "lines": _paint_lines,
    "plain": _paint_plain,
    "grid": _paint_grid,
    "dots": _paint_dots,
    "mm": _paint_mm,
}


def paper_px_height(model: PaperModel) -> float:
    """Экранная высота поля в px. Нужна обёртке тянущихся по ширине
    разлиновок: их высота обязана остаться заданной автором и в узкой
    колонке `row` тоже, а CSS листа сам её не выведет (см. `.paper-fluid`
    в assets.py)."""
    return (model.rows * PAPER_STEPS[model.ruling] + 1) * SCREEN_PX


def build_paper_svg(model: PaperModel) -> str:
    """SVG одного поля. Ширина в единицах viewBox — из `cols`, а без него
    номинальная ширина колонки; высота — всегда из `rows`. Единица —
    клетка/строка разлиновки (PAPER_STEPS, models.py).

    viewBox на единицу больше рисунка: рамка стоит по краю поля, и без
    этого запаса её штрих срезало бы границей SVG пополам."""
    step = PAPER_STEPS[model.ruling]
    w = model.cols * step if model.cols is not None else PAPER_NOMINAL_W
    h = model.rows * step
    view_w, view_h = w + 1, h + 1

    if model.cols is None:
        # Ширины в данных нет — поле занимает колонку целиком, растягиваясь
        # по горизонтали (см. модульный докстринг).
        size = (
            f'width="100%" height="{fmt_num(paper_px_height(model))}" '
            'preserveAspectRatio="none" '
        )
    else:
        size = (
            f'width="{fmt_num(view_w * SCREEN_PX)}" '
            f'height="{fmt_num(view_h * SCREEN_PX)}" '
        )

    inner = _RULING_PAINTERS[model.ruling](w, h)
    return (
        f'<svg class="visual-svg" viewBox="0 0 {view_w} {view_h}" {size}'
        'xmlns="http://www.w3.org/2000/svg">'
        f'<g transform="translate(0.5,0.5)">{inner}</g>'
        "</svg>"
    )
