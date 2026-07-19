"""Юнит-тесты генератора приборов (instruments.py): прореживание подписей
штрихов, привязка стрелки/уровня к показанию, поведение пустой шкалы.
Общий вид SVG фиксируют golden-тесты; здесь — точечные свойства, которые
golden не объясняет."""
import re

from worksheet_builder.instruments import _dial_point, _ticks, build_instrument_svg
from worksheet_builder.models import InstrumentModel


def make(kind="ammeter", unit="А", min=0, max=3, step=0.1, **extra):
    return InstrumentModel(type="instrument", kind=kind, unit=unit,
                           min=min, max=max, step=step, **extra)


def labeled_values(model):
    return [v for v, _, lab in _ticks(model) if lab]


def test_label_thinning_keeps_round_values():
    # 30 делений на дуге: подписан каждый 5-й штрих, включая оба предела.
    assert labeled_values(make()) == [0, 0.5, 1, 1.5, 2, 2.5, 3]
    # 25 делений мензурки: каждый 5-й (0, 50, ... 250).
    assert labeled_values(make(kind="cylinder", unit="мл", max=250, step=10)) == \
        [0, 50, 100, 150, 200, 250]
    # Миллиметровая линейка: подписан каждый сантиметр.
    assert labeled_values(make(kind="ruler", unit="см", max=10, step=0.1)) == \
        list(range(11))


def test_max_is_always_labeled():
    # 45 делений не кратно шагу подписей 10 — предел подписывается
    # принудительно: его читают в каждой задаче про пределы измерения.
    values = labeled_values(make(max=4.5))
    assert values[0] == 0 and values[-1] == 4.5


def test_negative_scale_labels():
    values = labeled_values(make(kind="thermometer", unit="°C", min=-10, max=50, step=1))
    assert values[0] == -10 and values[-1] == 50


def test_needle_angle_tracks_value():
    def needle_x(value):
        svg = build_instrument_svg(make(value=value))
        # Стрелка — последняя линия перед кружком опоры.
        needle = re.findall(r'<line [^>]*stroke-width="1.5"', svg)
        assert needle, svg
        return float(re.search(r'x2="([\d.]+)"', needle[-1]).group(1))

    assert needle_x(0) < 80 < needle_x(3)          # min слева, max справа
    assert abs(needle_x(1.5) - 80) < 0.1           # середина шкалы — вертикально
    # Пустая шкала — стрелка на нуле, как у value=min.
    svg_none = build_instrument_svg(make())
    svg_min = build_instrument_svg(make(value=0))
    assert svg_none == svg_min


def test_dial_point_geometry():
    x0, y0 = _dial_point(80, 88, 52, 0.0)
    x1, y1 = _dial_point(80, 88, 52, 1.0)
    assert x0 < 80 < x1
    assert abs(y0 - y1) < 1e-9  # симметричный размах


def test_ruler_value_draws_block():
    with_block = build_instrument_svg(make(kind="ruler", unit="см", max=10, step=0.1, value=6.4))
    empty = build_instrument_svg(make(kind="ruler", unit="см", max=10, step=0.1))
    assert with_block.count("<rect") == empty.count("<rect") + 1


def test_cylinder_level_tracks_value():
    def meniscus_y(value):
        svg = build_instrument_svg(
            make(kind="cylinder", unit="мл", max=250, step=10, value=value))
        line = re.search(r'<line x1="21.0" [^>]*stroke-width="1.2"', svg)
        assert line, svg
        return float(re.search(r'y1="([\d.]+)"', line.group(0)).group(1))

    assert meniscus_y(250) < meniscus_y(100) < meniscus_y(0)


def test_dual_scale_labels_share_ticks_and_are_round():
    # Шаблон школьного J0407: внешняя шкала 0-3 А, внутренняя 0-0.6 А.
    model = make(max=3, step=0.1, ranges=[0.6, 3], value=1.85)
    # Двойная шкала прореживается сильнее: подписи 0,1,2,3 — как на приборе.
    assert labeled_values(model) == [0, 1, 2, 3]
    svg = build_instrument_svg(model)
    labels = re.findall(r'<text x="([\d.]+)" y="([\d.]+)" font-size="7"[^>]*>([^<]+)</text>', svg)
    by_text = {text: (float(x), float(y)) for x, y, text in labels}
    # Каждая пара подписей (внешняя, внутренняя) стоит на одном штрихе:
    # позиции — ровно на радиусах 72 и 47 того же угла (+2.5 базлайн).
    for frac, outer, inner in [(1 / 3, "1", "0.2"), (2 / 3, "2", "0.4"), (1.0, "3", "0.6")]:
        ox, oy = _dial_point(80, 88, 72, frac)
        ix, iy = _dial_point(80, 88, 47, frac)
        assert by_text[outer] == (round(ox, 1), round(oy + 2.5, 1)), outer
        assert by_text[inner] == (round(ix, 1), round(iy + 2.5, 1)), inner
    # Клеммы: общий «−» и по одной на предел с подписью «0.6А»/«3А».
    assert "0.6А" in svg and "3А" in svg


def test_unit_and_caption_are_escaped():
    svg = build_instrument_svg(make(unit="a<b&", caption='c<d&"', value=1))
    assert "a<b" not in svg and "c<d" not in svg
    assert "a&lt;b&amp;" in svg and "c&lt;d&amp;&quot;" in svg


def test_unit_sup_becomes_tspan():
    svg = build_instrument_svg(make(kind="cylinder", unit="см<sup>3</sup>", max=100, step=5))
    assert "<sup>" not in svg
    assert 'baseline-shift="super"' in svg
