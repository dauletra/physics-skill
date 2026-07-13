"""Юнит-тесты генератора графиков (visuals.py): круглые деления осей и
конвертация <sup>/<sub> в SVG-совместимый <tspan> в подписях осей. Общий вид
SVG фиксируют golden-тесты; здесь — точечные свойства, которые golden не
объясняет."""
import re

from worksheet_builder.visuals import _tick_positions, build_chart_svg


def test_ticks_are_round_for_awkward_range():
    # Раньше: linspace на 6 делений -> 0, 1.4, 2.8... Ученик считывает
    # значения по сетке, шаг обязан быть круглым (1/2/5 x 10^n).
    assert _tick_positions(0, 7) == [0, 1, 2, 3, 4, 5, 6, 7]
    assert _tick_positions(250, 650) == [250, 300, 350, 400, 450, 500, 550, 600, 650]
    assert _tick_positions(0, 10) == [0, 2, 4, 6, 8, 10]


def test_ticks_stay_inside_range_and_bounded():
    for lo, hi in [(0.9, 7.1), (0, 0.35), (13, 940), (-5, 5)]:
        ticks = _tick_positions(lo, hi)
        assert 2 <= len(ticks) <= 9, (lo, hi, ticks)
        assert all(lo - 1e-9 <= t <= hi + 1e-9 for t in ticks), (lo, hi, ticks)


def _chart(**overrides):
    kwargs = dict(x_label="t, с", y_label="υ, м/с",
                  x_range=(0, 5), y_range=(0, 10), series=[])
    kwargs.update(overrides)
    return build_chart_svg(**kwargs)


def test_sup_sub_in_axis_labels_become_tspan():
    # Буквальный <sup> внутри SVG <text> невалиден и молча ломает отрисовку.
    svg = _chart(x_label="a, м/с<sup>2</sup>", y_label="x<sub>max</sub>")
    assert "<sup>" not in svg and "<sub>" not in svg
    assert svg.count('baseline-shift="super"') == 1
    assert svg.count('baseline-shift="sub"') == 1


def test_axis_labels_still_escaped():
    svg = _chart(x_label="a < b & c")
    assert "a &lt; b &amp; c" in svg


def test_fractional_ticks_have_no_float_noise():
    # Шаг 0.05: подписи вида "0.15", а не "0.15000000000000002".
    svg = _chart(x_range=(0, 0.35))
    labels = re.findall(r'text-anchor="middle">([^<]+)<', svg)
    assert all(len(label) <= 4 for label in labels), labels
