"""Генерация SVG приборов со шкалой (`build_instrument_svg`) для компонента
`instrument` (components.py). Геометрий три — по семействам из
`INSTRUMENT_FAMILIES` (models.py):

- `strip`  — горизонтальная линейка (опционально с измеряемым бруском);
- `column` — вертикальная шкала: мензурка, термометр, динамометр;
- `dial`   — стрелочный циферблат: амперметр, вольтметр, манометр,
  циферблатные весы, спидометр.

Конвенции — references/artifacts/README.md: только ч/б, авторский текст
через `esc()`/`svg_label()`, числа через `fmt_num()`. У каждого семейства
свой viewBox и своя целевая экранная ширина (max-width у
`.instrument-wrap.instrument-<семейство>` в BASE_CSS) — масштаб везде
~1.5px на единицу viewBox, чтобы шрифты всех SVG листа были одного
экранного размера. Внутри SVG нет `id`/`defs`/`pattern`: на листе может
стоять несколько приборов, а id в HTML глобальны — штриховки рисуются
явными линиями."""

import math
from decimal import Decimal
from typing import Callable

from worksheet_builder.models import INSTRUMENT_FAMILIES, InstrumentModel
from worksheet_builder.render_helpers import esc, fmt_num, svg_label

SVG_OPEN = (
    '<svg class="visual-svg" viewBox="0 0 {w} {h}" '
    'xmlns="http://www.w3.org/2000/svg" '
    'font-family="PT Sans, Segoe UI, Verdana, Arial, sans-serif">'
)

# Прореживание подписей: подписывается каждый k-й штрих от min. Лимиты —
# per-семейство: линейка традиционно несёт больше чисел (каждый сантиметр),
# чем дуга или столбик; полный круг секундомера — до 12 (как часовой
# циферблат). 25 в ряду — ради круглых подписей секундомера (0–30 с × 0,2:
# подпись каждые 5 с).
_LABEL_EVERY = (1, 2, 5, 10, 20, 25, 50)
_MAX_LABELS = {"strip": 16, "column": 8, "dial": 8, "clock": 12, "vernier": 6}


def _ticks(model: InstrumentModel) -> list[tuple[float, float, bool]]:
    """Штрихи шкалы: (значение, доля 0..1 вдоль шкалы, подписан ли).

    Прореживание подписей — представление, а не данные (принципы схемы,
    п. 10), поэтому вычисляется здесь: k — минимальный из _LABEL_EVERY,
    дающий не больше лимита подписей семейства; предпочитается k, делящий
    число делений нацело. Предел шкалы подписывается всегда (его читают в
    любой задаче про пределы измерения); если max не попал в k-сетку,
    снимается регулярная подпись ближе полушага к нему — иначе две подписи
    слипнутся."""
    n = round((model.max - model.min) / model.step)
    max_labels = _MAX_LABELS[INSTRUMENT_FAMILIES[model.kind]]
    # Двойная шкала несёт два ряда чисел на каждый подписанный штрих —
    # прореживаем сильнее, как на реальном приборе (0-3 А: подписи 0,1,2,3).
    if model.ranges:
        max_labels = 5
    fitting = [k for k in _LABEL_EVERY if n // k + 1 <= max_labels]
    if not fitting:
        fitting = [_LABEL_EVERY[-1]]
    k = next((k for k in fitting if n % k == 0), fitting[0])
    result = []
    for i in range(n + 1):
        labeled = i == n or (i % k == 0 and (n - i) * 2 >= k)
        result.append((model.min + i * model.step, i / n, labeled))
    return result


def _value_frac(model: InstrumentModel) -> float:
    """Доля 0..1 вдоль шкалы для показания; пустая шкала — стрелка/уровень
    на нуле шкалы."""
    if model.value is None:
        return 0.0
    return (model.value - model.min) / (model.max - model.min)


def _text(x: float, y: float, content: str, size: float, anchor: str = "middle") -> str:
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
        f'text-anchor="{anchor}">{content}</text>'
    )


def _line(x1: float, y1: float, x2: float, y2: float, width: float) -> str:
    return (
        f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
        f'stroke="#000" stroke-width="{width}"/>'
    )


# --- strip: линейка ---

def _build_strip(model: InstrumentModel) -> str:
    """Линейка. Шкала штрихами вниз от верхней кромки корпуса; `value` —
    правый край заштрихованного бруска, лежащего на кромке от нуля шкалы
    (задачи «определи длину/запиши с погрешностью»)."""
    w, h = 220, 52
    body_top, body_bottom = 17.5, 48.5
    x0, x1 = 12.0, 208.0

    def sx(frac: float) -> float:
        return x0 + frac * (x1 - x0)

    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        f'<rect x="1.5" y="{body_top}" width="217" height="{body_bottom - body_top}" '
        'rx="2" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    ticks = _ticks(model)
    # Средний штрих (как 5-мм на настоящей линейке) — на полпути между
    # подписанными, если подписи прорежены чётным шагом.
    labeled_idx = [i for i, (_, _, lab) in enumerate(ticks) if lab]
    k = labeled_idx[1] - labeled_idx[0] if len(labeled_idx) > 1 else 1
    for i, (value, frac, labeled) in enumerate(ticks):
        x = sx(frac)
        length = 9 if labeled else 7 if (k >= 4 and k % 2 == 0 and i % (k // 2) == 0) else 5
        parts.append(_line(x, body_top, x, body_top + length, 0.9 if labeled else 0.5))
        if labeled:
            parts.append(_text(x, body_top + 17.5, fmt_num(value), 7))
    parts.append(_text(x1, body_bottom - 3.5, svg_label(model.unit), 7, anchor="end"))
    if model.value is not None:
        # Брусок: от нуля шкалы до value, лежит на верхней кромке.
        right = sx(_value_frac(model))
        parts.append(
            f'<rect x="{sx(0):.1f}" y="4.5" width="{right - sx(0):.1f}" height="13" '
            'fill="#fff" stroke="#000" stroke-width="1"/>'
        )
        parts.extend(_hatch_rect(sx(0), 4.5, right, body_top))
    parts.append("</svg>")
    return "".join(parts)


def _hatch_rect(x0: float, y0: float, x1: float, y1: float, spacing: float = 4.5) -> list[str]:
    """Диагональная штриховка прямоугольника явными линиями 45° (без
    defs/pattern — id глобальны в HTML, а приборов на листе несколько)."""
    lines = []
    height = y1 - y0
    d = spacing * math.sqrt(2)
    offset = d
    while offset < (x1 - x0) + height:
        ax = x0 + offset
        ay = y0
        if ax > x1:
            ay = y0 + (ax - x1)
            ax = x1
        bx = x0 + offset - height
        by = y1
        if bx < x0:
            by = y1 - (x0 - bx)
            bx = x0
        lines.append(
            f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" '
            'stroke="#000" stroke-width="0.4"/>'
        )
        offset += d
    return lines


# --- column: мензурка, термометр, динамометр ---

def _column_scale(
    parts: list[str],
    model: InstrumentModel,
    scale_x: float,
    tick_dir: int,
    label_x: float,
    label_anchor: str,
    y_top: float,
    y_bottom: float,
) -> Callable[[float], float]:
    """Общая вертикальная шкала семейства: штрихи от `scale_x` в сторону
    `tick_dir` (+1 вправо, −1 влево), подписи у `label_x`. Возвращает
    маппер доли 0..1 -> y (0 = min внизу)."""

    def sy(frac: float) -> float:
        return y_bottom - frac * (y_bottom - y_top)

    for value, frac, labeled in _ticks(model):
        y = sy(frac)
        length = 9 if labeled else 5.5
        parts.append(_line(scale_x, y, scale_x + tick_dir * length, y, 0.8 if labeled else 0.5))
        if labeled:
            parts.append(_text(label_x, y + 2.4, fmt_num(value), 7, anchor=label_anchor))
    return sy


def _build_cylinder(model: InstrumentModel) -> str:
    """Мензурка: открытый сверху сосуд, шкала на левой стенке, уровень
    жидкости — линия-мениск + горизонтальная штриховка (учебная конвенция
    для жидкости)."""
    w, h = 70, 160
    left, right, top, bottom = 20.0, 56.0, 8.0, 148.0
    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        f'<path d="M{left},{top} V{bottom} H{right} V{top}" '
        'fill="none" stroke="#000" stroke-width="1.2"/>'
    )
    sy = _column_scale(parts, model, left, +1, left - 3, "end", y_top=18, y_bottom=138)
    parts.append(_text(right + 2, top + 5, svg_label(model.unit), 7, anchor="start"))
    if model.value is not None:
        level = sy(_value_frac(model))
        parts.append(_line(left + 1, level, right - 1, level, 1.2))
        y = level + 4
        while y < bottom - 2:
            parts.append(_line(left + 1.5, y, right - 1.5, y, 0.4))
            y += 4
    return "".join(parts) + "</svg>"


def _build_thermometer(model: InstrumentModel) -> str:
    """Термометр: трубка с резервуаром, шкала справа от трубки, столбик —
    заливка от резервуара до показания (пустая шкала — только резервуар)."""
    w, h = 70, 160
    cx = 32.0
    tube_top, tube_bottom = 12.5, 130.0
    bulb_y, bulb_r = 141.0, 9.5
    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        f'<rect x="{cx - 6}" y="{tube_top}" width="12" height="{tube_bottom - tube_top}" '
        'rx="6" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    parts.append(
        f'<circle cx="{cx}" cy="{bulb_y}" r="{bulb_r}" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    sy = _column_scale(parts, model, cx + 6, +1, cx + 14.5, "start", y_top=22, y_bottom=122)
    parts.append(_text(cx, 8.8, svg_label(model.unit), 7))
    column_top = sy(_value_frac(model)) if model.value is not None else tube_bottom - 4
    parts.append(
        f'<rect x="{cx - 2.5}" y="{column_top:.1f}" width="5" '
        f'height="{tube_bottom - 2 - column_top:.1f}" fill="#000"/>'
    )
    parts.append(f'<circle cx="{cx}" cy="{bulb_y}" r="{bulb_r - 3}" fill="#000"/>')
    return "".join(parts) + "</svg>"


def _build_dynamometer(model: InstrumentModel) -> str:
    """Динамометр: корпус с кольцом сверху и крюком снизу, шкала по центру
    корпуса, показание — горизонтальная риска-указатель."""
    w, h = 70, 160
    cx = 38.0
    body_left, body_right = 22.0, 54.0
    body_top, body_bottom = 16.0, 128.0
    parts = [SVG_OPEN.format(w=w, h=h)]
    # Кольцо для подвеса и крюк.
    parts.append(f'<circle cx="{cx}" cy="8" r="4.5" fill="none" stroke="#000" stroke-width="1"/>')
    parts.append(_line(cx, 12.5, cx, body_top, 1))
    parts.append(_line(cx, body_bottom, cx, 138, 1))
    parts.append(
        f'<path d="M{cx},138 C{cx + 8},140 {cx + 8},152 {cx - 1},152 '
        f'C{cx - 6},152 {cx - 8},148 {cx - 7},145" '
        'fill="none" stroke="#000" stroke-width="1.2"/>'
    )
    parts.append(
        f'<rect x="{body_left}" y="{body_top}" width="{body_right - body_left}" '
        f'height="{body_bottom - body_top}" rx="3" fill="#fff" stroke="#000" stroke-width="1.2"/>'
    )
    parts.append(_text(cx + 8, body_top + 10, svg_label(model.unit), 7))
    scale_x = cx + 2
    sy = _column_scale(
        parts, model, scale_x, +1, scale_x - 3.5, "end", y_top=body_top + 14, y_bottom=body_bottom - 8
    )
    pointer_y = sy(_value_frac(model))
    parts.append(_line(body_left + 3, pointer_y, scale_x + 9, pointer_y, 1.3))
    return "".join(parts) + "</svg>"


# --- dial: стрелочные приборы ---

# Дуга шкалы: от 150° (min, слева) до 30° (max, справа) в математических
# градусах — стрелка ходит через вертикаль, размах 120°.
_DIAL_START, _DIAL_SWEEP = 150.0, 120.0


def _dial_point(cx: float, cy: float, r: float, frac: float) -> tuple[float, float]:
    theta = math.radians(_DIAL_START - frac * _DIAL_SWEEP)
    return cx + r * math.cos(theta), cy - r * math.sin(theta)


def _build_dial(model: InstrumentModel) -> str:
    """Стрелочный прибор: корпус, дуговая шкала, стрелка от опоры к
    показанию. У электроизмерительных (амперметр/вольтметр) — единица в
    кружке и клеммы «+»/«−», у остальных — единица текстом. Метрология:
    класс точности печатается числом в левом нижнем углу (как на настоящей
    шкале); двухпредельный прибор (`ranges`) несёт двойную шкалу — штрихи
    общие, над дугой подписи большего предела (внешняя шкала), под дугой —
    меньшего (значение × отношение пределов), и три клеммы: «−» и по одной
    на предел с подписью."""
    w, h = 160, 110
    cx, cy = 80.0, 88.0
    r_arc, r_needle, r_label = 58.0, 52.0, 72.0
    electric = model.kind in ("ammeter", "voltmeter")
    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        f'<rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="6" '
        'fill="#fff" stroke="#000" stroke-width="1.2"/>'
    )
    ax0, ay0 = _dial_point(cx, cy, r_arc, 0.0)
    ax1, ay1 = _dial_point(cx, cy, r_arc, 1.0)
    parts.append(
        f'<path d="M{ax0:.1f},{ay0:.1f} A{r_arc},{r_arc} 0 0 1 {ax1:.1f},{ay1:.1f}" '
        'fill="none" stroke="#000" stroke-width="1"/>'
    )
    # Внутренняя шкала двухпредельного прибора: то же значение × отношение
    # пределов, подпись под дугой на том же штрихе.
    inner_ratio = model.ranges[0] / model.ranges[-1] if model.ranges else None
    r_inner = 47.0
    for value, frac, labeled in _ticks(model):
        tx0, ty0 = _dial_point(cx, cy, r_arc, frac)
        tx1, ty1 = _dial_point(cx, cy, r_arc + (7.5 if labeled else 4.5), frac)
        parts.append(_line(tx0, ty0, tx1, ty1, 0.9 if labeled else 0.5))
        if labeled:
            lx, ly = _dial_point(cx, cy, r_label, frac)
            parts.append(_text(lx, ly + 2.5, fmt_num(value), 7))
            if inner_ratio is not None:
                ix, iy = _dial_point(cx, cy, r_inner, frac)
                parts.append(_text(ix, iy + 2.5, fmt_num(value * inner_ratio), 7))
    # Единица измерения. Кружок (как на школьных электроизмерительных
    # приборах) — только для коротких единиц («А», «В»); длинная («дел.»
    # у многопредельной шкалы) в кружок не помещается — печатается текстом.
    if electric and len(model.unit) <= 2:
        parts.append(
            f'<circle cx="{cx}" cy="66" r="8" fill="#fff" stroke="#000" stroke-width="0.8"/>'
        )
    parts.append(_text(cx, 68.8, svg_label(model.unit), 8))
    # Стрелка поверх единицы, опора — заливной кружок.
    nx, ny = _dial_point(cx, cy, r_needle, _value_frac(model))
    parts.append(_line(cx, cy, nx, ny, 1.5))
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="3.5" fill="#000"/>')
    if model.accuracy_class is not None:
        # Как на настоящей шкале: просто число в углу (расшифровка
        # обозначения — задача условия, а не рисунка).
        parts.append(_text(10, 103, fmt_num(model.accuracy_class), 7, anchor="start"))
    if electric:
        if model.ranges:
            # Как на реальном приборе: общая клемма «−» и по клемме на
            # предел с подписью «0.6А»/«3А». Куда «включён» провод, рисунок
            # не знает — это текст условия задачи.
            labels = ["&#8722;"] + [
                f"{fmt_num(r)}{svg_label(model.unit)}" for r in model.ranges
            ]
            for j, label in enumerate(labels):
                tx = 36 + j * 88 / (len(labels) - 1)
                parts.append(
                    f'<circle cx="{tx:.1f}" cy="99" r="3" fill="#fff" '
                    'stroke="#000" stroke-width="1"/>'
                )
                parts.append(_text(tx, 93, label, 6))
        else:
            for tx, sign in ((58.0, "+"), (102.0, "&#8722;")):
                parts.append(
                    f'<circle cx="{tx}" cy="99" r="3" fill="#fff" stroke="#000" stroke-width="1"/>'
                )
                parts.append(_text(tx + (-8 if sign == "+" else 8), 102, sign, 8))
    return "".join(parts) + "</svg>"


# --- vernier: штангенциркуль ---

def _build_caliper(model: InstrumentModel) -> str:
    """Штангенциркуль: штанга со шкалой (штрихи вверх от нижней кромки),
    рамка с нониусом под ней, губки вниз, между губками — заштрихованная
    деталь шириной `value`. Штрих i нониуса стоит на
    `value + i·step·(v−1)/v`, поэтому при `value = n·step + k·(step/v)`
    ровно k-й штрих нониуса совпадает со штрихом штанги — классический
    отсчёт по совпадению. Точность (step/v) на рисунке не печатается —
    она выводится учеником из числа делений нониуса."""
    w, h = 220, 84
    x0, x1 = 14.0, 206.0
    bar_top, bar_bottom = 16.0, 40.0
    frame_bottom, jaw_bottom = 58.0, 78.0
    v = model.vernier or 10

    def sx(val: float) -> float:
        return x0 + (val - model.min) / (model.max - model.min) * (x1 - x0)

    value = model.value if model.value is not None else model.min
    xv = sx(value)
    parts = [SVG_OPEN.format(w=w, h=h)]
    # Штанга и неподвижная губка (измерительная плоскость — при нуле шкалы).
    parts.append(
        f'<rect x="2" y="{bar_top}" width="216" height="{bar_bottom - bar_top}" '
        'fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    parts.append(
        f'<rect x="{x0 - 6:.1f}" y="{bar_bottom}" width="6" '
        f'height="{jaw_bottom - bar_bottom}" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    # Шкала штанги: штрихи вверх от нижней кромки — навстречу нониусу.
    for tick_value, frac, labeled in _ticks(model):
        x = sx(tick_value)
        length = 7.0 if labeled else 4.5
        parts.append(_line(x, bar_bottom, x, bar_bottom - length, 0.9 if labeled else 0.5))
        if labeled:
            parts.append(_text(x, bar_bottom - 9.5, fmt_num(tick_value), 7))
    parts.append(_text(x1, bar_top + 8.5, svg_label(model.unit), 7, anchor="end"))
    # Рамка с нониусом и подвижная губка (измерительная плоскость — слева).
    frame_w = sx(value + (v - 1) * model.step) - xv + 8
    parts.append(
        f'<rect x="{xv:.1f}" y="{bar_bottom}" width="{frame_w:.1f}" '
        f'height="{frame_bottom - bar_bottom}" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    parts.append(
        f'<rect x="{xv:.1f}" y="{bar_bottom}" width="6" '
        f'height="{jaw_bottom - bar_bottom}" fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    for i in range(v + 1):
        x = sx(value + i * model.step * (v - 1) / v)
        labeled = i in (0, v // 2, v)
        parts.append(_line(x, bar_bottom, x, bar_bottom + (6.0 if labeled else 4.0),
                           0.9 if labeled else 0.5))
        if labeled:
            parts.append(_text(x, bar_bottom + 14.5, str(i), 6))
    # Деталь между губками.
    if model.value is not None and model.value > model.min:
        parts.append(
            f'<rect x="{x0:.1f}" y="60" width="{xv - x0:.1f}" height="14" '
            'fill="#fff" stroke="#000" stroke-width="1"/>'
        )
        parts.extend(_hatch_rect(x0, 60, xv, 74))
    return "".join(parts) + "</svg>"


# --- clock: секундомер (полная круговая шкала) ---

def _clock_point(cx: float, cy: float, r: float, frac: float) -> tuple[float, float]:
    # Нуль сверху, ход по часовой стрелке, полный оборот.
    theta = math.radians(90.0 - frac * 360.0)
    return cx + r * math.cos(theta), cy - r * math.sin(theta)


def _build_stopwatch(model: InstrumentModel) -> str:
    """Механический секундомер: полная круговая шкала, нуль сверху, ход по
    часовой стрелке. Точки min и max совпадают наверху — штрих нуля не
    рисуется, в верхней точке подписан предел (как «30»/«60» на настоящем
    секундомере). Сверху — кнопка-заводная головка."""
    w, h = 120, 132
    cx, cy = 60.0, 74.0
    r_body, r_arc, r_needle, r_label = 54.0, 47.0, 38.0, 33.0
    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        '<rect x="55" y="6" width="10" height="9" rx="1.5" '
        'fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    parts.append(_line(60.0, 15.0, 60.0, 20.0, 1.2))
    parts.append(
        f'<circle cx="{cx}" cy="{cy}" r="{r_body}" fill="#fff" stroke="#000" stroke-width="1.2"/>'
    )
    for i, (value, frac, labeled) in enumerate(_ticks(model)):
        if i == 0:
            continue  # совпадает с точкой max наверху
        x0, y0 = _clock_point(cx, cy, r_arc, frac)
        x1, y1 = _clock_point(cx, cy, r_arc - (7.0 if labeled else 4.0), frac)
        parts.append(_line(x0, y0, x1, y1, 0.9 if labeled else 0.5))
        if labeled:
            lx, ly = _clock_point(cx, cy, r_label, frac)
            parts.append(_text(lx, ly + 2.4, fmt_num(value), 7))
    parts.append(_text(cx, cy + 21, svg_label(model.unit), 7))
    nx, ny = _clock_point(cx, cy, r_needle, _value_frac(model))
    parts.append(_line(cx, cy, nx, ny, 1.3))
    parts.append(f'<circle cx="{cx}" cy="{cy}" r="3" fill="#000"/>')
    return "".join(parts) + "</svg>"


# --- balance: рычажные весы с гирями ---

def _build_balance(model: InstrumentModel) -> str:
    """Рычажные весы: стойка на основании, горизонтальное коромысло на
    опоре, две чашки на нитях; слева — заштрихованное тело (`value` — его
    масса), справа — гири (`weights`, рисуются по убыванию с подписями
    масс, повторы разрешены). Весы всегда **в равновесии** (стрелка на
    контрольной риске): рисунок — постановка задачи, а не симуляция, и
    согласованность масс — дело условия, а не рендера. Чашки комбинируются
    свободно: тело + гири, тело + пустая чаша («какие гири положить?»),
    только гири, пустые весы. Предел взвешивания — мелкой строкой у
    основания."""
    w, h = 170, 86
    cx, beam_y = 85.0, 28.0
    lx, rx = cx - 58.0, cx + 58.0
    pan_y = beam_y + 30.0
    parts = [SVG_OPEN.format(w=w, h=h)]

    # Основание, стойка, контрольная риска и предел взвешивания.
    parts.append(
        f'<rect x="{cx - 26:.1f}" y="74" width="52" height="5" '
        'fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    parts.append(_line(cx, 74.0, cx, beam_y, 1.5))
    parts.append(_line(cx - 4, 52.0, cx + 4, 52.0, 0.5))
    parts.append(
        _text(6, 83.5,
              f"{fmt_num(model.min)}&#8230;{fmt_num(model.max)} {svg_label(model.unit)}",
              6, anchor="start")
    )

    # Коромысло, стрелка на риске, опора.
    parts.append(_line(lx, beam_y, rx, beam_y, 1.8))
    parts.append(_line(cx, beam_y, cx, 50.0, 1))
    parts.append(f'<circle cx="{cx}" cy="{beam_y}" r="2.5" fill="#000"/>')

    # Чашки: две нити от конца коромысла к краям тарелки.
    for ex in (lx, rx):
        parts.append(_line(ex, beam_y, ex - 20, pan_y, 0.7))
        parts.append(_line(ex, beam_y, ex + 20, pan_y, 0.7))
        parts.append(_line(ex - 20, pan_y, ex + 20, pan_y, 1.2))

    # Тело на левой чашке.
    if model.value is not None:
        parts.append(
            f'<rect x="{lx - 11:.1f}" y="{pan_y - 13:.1f}" width="22" height="13" '
            'fill="#fff" stroke="#000" stroke-width="1"/>'
        )
        parts.extend(_hatch_rect(lx - 11, pan_y - 13, lx + 11, pan_y))

    # Гири на правой чашке: по убыванию, высота пропорциональна массе,
    # маленькая головка сверху, подпись массы над гирей.
    if model.weights:
        ordered = sorted(model.weights, reverse=True)
        biggest = ordered[0]
        gw, gap = 8.0, 2.0
        x = rx - (len(ordered) * gw + (len(ordered) - 1) * gap) / 2
        for wt in ordered:
            gh = 6.0 + 8.0 * wt / biggest
            top = pan_y - gh
            parts.append(
                f'<rect x="{x:.1f}" y="{top:.1f}" width="{gw}" height="{gh:.1f}" '
                'fill="#fff" stroke="#000" stroke-width="1"/>'
            )
            parts.append(
                f'<rect x="{x + gw / 2 - 1.5:.1f}" y="{top - 2:.1f}" width="3" height="2" '
                'fill="#000"/>'
            )
            parts.append(_text(x + gw / 2, top - 4, fmt_num(wt), 6))
            x += gw + gap
    return "".join(parts) + "</svg>"


# --- digital: приборы с цифровым табло ---

def _build_digital(model: InstrumentModel) -> str:
    """Цифровой прибор (мультиметр, электронные весы, электронный
    секундомер): корпус с табло. Показание печатается с числом десятичных
    знаков цены деления — `step` здесь означает **дискретность** (единицу
    младшего разряда): 12.47 при step 0.01; пустой прибор показывает нули.
    Диапазон измерения — мелкой строкой под табло."""
    w, h = 150, 64
    parts = [SVG_OPEN.format(w=w, h=h)]
    parts.append(
        '<rect x="1.5" y="1.5" width="147" height="61" rx="5" '
        'fill="#fff" stroke="#000" stroke-width="1.2"/>'
    )
    parts.append(
        '<rect x="10" y="10" width="130" height="28" '
        'fill="#fff" stroke="#000" stroke-width="1"/>'
    )
    # Точное десятичное представление, не fmt_num: тот обрезает всё мельче
    # сотых, и step 0.001 давал бы 0 знаков. normalize() гасит хвост «.0» у
    # целых step; step валидирован конечным, так что exponent всегда int.
    exponent = Decimal(str(model.step)).normalize().as_tuple().exponent
    decimals = max(0, -int(exponent))
    value = model.value if model.value is not None else 0
    parts.append(
        f'<text x="116" y="31.5" font-size="15" text-anchor="end" '
        f'font-weight="bold" letter-spacing="1">{value:.{decimals}f}</text>'
    )
    parts.append(_text(136, 31.5, svg_label(model.unit), 8))
    parts.append(
        _text(10, 55,
              f"{fmt_num(model.min)}…{fmt_num(model.max)} {svg_label(model.unit)}",
              7, anchor="start")
    )
    return "".join(parts) + "</svg>"


_FAMILY_BUILDERS: dict[str, Callable[[InstrumentModel], str]] = {
    "ruler": _build_strip,
    "cylinder": _build_cylinder,
    "thermometer": _build_thermometer,
    "dynamometer": _build_dynamometer,
    "ammeter": _build_dial,
    "voltmeter": _build_dial,
    "manometer": _build_dial,
    "scale_dial": _build_dial,
    "speedometer": _build_dial,
    "stopwatch": _build_stopwatch,
    "caliper": _build_caliper,
    "balance": _build_balance,
    "multimeter": _build_digital,
    "digital_scale": _build_digital,
    "digital_stopwatch": _build_digital,
}


def build_instrument_svg(model: InstrumentModel) -> str:
    """SVG прибора + опциональная подпись, обёрнутые в div семейства —
    CSS-ширина висит на `.instrument-wrap.instrument-<семейство>`
    (см. BASE_CSS в assets.py и references/design-system.md)."""
    svg = _FAMILY_BUILDERS[model.kind](model)
    caption = (
        f'<div class="instrument-caption">{esc(model.caption)}</div>' if model.caption else ""
    )
    family = INSTRUMENT_FAMILIES[model.kind]
    return f'<div class="instrument-wrap instrument-{family}">{svg}{caption}</div>'
