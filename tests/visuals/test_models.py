"""What the three ported types refuse, and why.

Each case is a mistake an author can actually make; the assertion is on the
fragment of the message that tells them what to change. A rejection whose
message does not name the culprit is only half a validation.
"""

from __future__ import annotations

import pytest

from physics_svg.schema import SchemaError
from physics_svg.visuals import parse_visual

GRAPH = {
    "type": "graph",
    "x_label": "t, с",
    "y_label": "υ, м/с",
    "x_range": [0, 8],
    "y_range": [0, 20],
}
RULER = {"type": "instrument", "kind": "ruler", "unit": "см", "min": 0, "max": 10, "step": 0.1}
DIAL = {"type": "instrument", "kind": "ammeter", "unit": "А", "min": 0, "max": 2, "step": 0.05}
PAPER = {"type": "paper", "ruling": "lines", "rows": 4}


def rejects(data: dict, fragment: str) -> None:
    with pytest.raises(SchemaError) as info:
        parse_visual(data)
    assert fragment in str(info.value), f"ожидался фрагмент {fragment!r}, получено:\n{info.value}"


class TestGraph:
    def test_reversed_range(self) -> None:
        rejects({**GRAPH, "y_range": [20, 0]}, "min < max")

    def test_bar_with_two_series(self) -> None:
        rejects(
            {
                **GRAPH,
                "chart_type": "bar",
                "series": [{"points": [[1, 2]]}, {"points": [[2, 3]]}],
            },
            "только одну серию",
        )

    def test_bar_not_starting_at_zero(self) -> None:
        # A bar that does not grow from zero lies about the ratio of heights.
        rejects({**GRAPH, "chart_type": "bar", "y_range": [5, 20]}, "должна начинаться с нуля")

    def test_empty_series(self) -> None:
        rejects({**GRAPH, "series": [{"points": []}]}, "хотя бы 1")

    def test_unknown_chart_type(self) -> None:
        rejects({**GRAPH, "chart_type": "pie"}, "недопустимое значение")

    def test_axes_without_series_are_valid(self) -> None:
        assert parse_visual(GRAPH).series == []


class TestGraphDivisions:
    """A pinned scale: the author's numbers must land on the axis and stay
    readable. Nothing is checked while the renderer chooses for itself."""

    def test_step_must_divide_the_range(self) -> None:
        rejects({**GRAPH, "x_step": 3}, "укладываться в диапазон")

    def test_label_step_must_divide_the_range(self) -> None:
        rejects({**GRAPH, "y_range": [0, 25], "y_label_step": 10}, "укладываться в диапазон")

    def test_label_step_must_land_on_a_tick(self) -> None:
        rejects({**GRAPH, "x_step": 2, "x_label_step": 3}, "кратен цене деления")

    def test_ticks_too_dense_to_read(self) -> None:
        rejects({**GRAPH, "x_step": 0.05}, "засечки сольются")

    def test_labels_too_dense_to_read(self) -> None:
        rejects({**GRAPH, "y_range": [0, 20], "y_label_step": 1}, "налезут друг на друга")

    def test_pinned_scale_is_kept(self) -> None:
        model = parse_visual({**GRAPH, "x_range": [0, 40], "x_step": 5, "x_label_step": 10})
        assert (model.x_step, model.x_label_step) == (5, 10)

    def test_a_step_alone_is_enough(self) -> None:
        assert parse_visual({**GRAPH, "x_step": 2}).x_label_step is None

    def test_grid_can_be_switched_off(self) -> None:
        assert parse_visual({**GRAPH, "grid": "none"}).grid == "none"


class TestInstrumentScale:
    def test_step_must_divide_the_range(self) -> None:
        rejects({**RULER, "step": 0.3}, "укладываться в шкалу нацело")

    def test_too_many_divisions(self) -> None:
        rejects({**RULER, "step": 0.01}, "от 2 до 150 делений")

    def test_reading_outside_the_scale(self) -> None:
        rejects({**RULER, "value": 12}, "вне шкалы")

    def test_reading_between_ticks_is_allowed(self) -> None:
        # The whole point of reading-error problems.
        assert parse_visual({**DIAL, "value": 1.37}).value == 1.37

    def test_label_step_must_land_on_ticks(self) -> None:
        rejects({**RULER, "label_step": 0.15}, "кратен цене деления")

    def test_label_step_over_the_readable_limit(self) -> None:
        rejects({**RULER, "label_step": 0.2}, "читаемого предела")

    def test_label_step_on_a_display(self) -> None:
        rejects(
            {"type": "instrument", "kind": "multimeter", "unit": "В", "min": 0, "max": 20,
             "step": 0.01, "label_step": 1},
            "штриховой шкалой",
        )


class TestInstrumentMetrology:
    def test_accuracy_class_outside_the_standard(self) -> None:
        rejects({**DIAL, "accuracy_class": 3.0}, "класс точности должен быть")

    def test_accuracy_class_on_a_ruler(self) -> None:
        rejects({**RULER, "accuracy_class": 1.5}, "только на стрелочных")

    def test_ranges_only_on_electrical_instruments(self) -> None:
        rejects({**RULER, "ranges": [1, 10]}, "двухпредельная шкала")

    def test_max_must_be_the_larger_range(self) -> None:
        rejects({**DIAL, "ranges": [0.6, 3]}, "должен совпадать с большим пределом")

    def test_ranges_must_increase(self) -> None:
        rejects({**DIAL, "max": 3, "step": 0.1, "ranges": [3, 0.6]}, "строго возрастать")

    def test_a_dual_scale_may_run_below_zero(self) -> None:
        model = parse_visual(
            {**DIAL, "min": -1, "max": 3, "step": 0.1, "ranges": [0.6, 3], "value": 1.85}
        )
        assert model.min == -1

    def test_digital_reading_is_a_multiple_of_the_resolution(self) -> None:
        rejects(
            {"type": "instrument", "kind": "digital_scale", "unit": "г", "min": 0, "max": 500,
             "step": 0.1, "value": 248.33},
            "кратно дискретности",
        )


class TestInstrumentEquipment:
    def test_vernier_only_on_a_caliper(self) -> None:
        rejects({**RULER, "vernier": 10}, "только у штангенциркуля")

    def test_caliper_reading_must_be_readable(self) -> None:
        rejects(
            {"type": "instrument", "kind": "caliper", "unit": "мм", "min": 0, "max": 40,
             "step": 1, "vernier": 10, "value": 27.43},
            "кратно точности нониуса",
        )

    def test_vernier_must_fit_on_the_bar(self) -> None:
        rejects(
            {"type": "instrument", "kind": "caliper", "unit": "мм", "min": 0, "max": 40,
             "step": 1, "vernier": 10, "value": 39},
            "помещаться на штанге",
        )

    def test_weights_only_on_a_balance(self) -> None:
        rejects({**RULER, "weights": [10]}, "только у рычажных весов")

    def test_weights_are_multiples_of_the_smallest(self) -> None:
        rejects(
            {"type": "instrument", "kind": "balance", "unit": "г", "min": 0, "max": 200,
             "step": 1, "weights": [10.5]},
            "кратна наименьшей гире",
        )

    def test_weights_within_the_weighing_limit(self) -> None:
        rejects(
            {"type": "instrument", "kind": "balance", "unit": "г", "min": 0, "max": 100,
             "step": 1, "weights": [50, 50, 50]},
            "больше предела взвешивания",
        )


class TestPaper:
    def test_square_rulings_need_a_width(self) -> None:
        rejects({"type": "paper", "ruling": "mm", "rows": 12}, "нужно поле 'cols'")

    def test_wider_than_the_column(self) -> None:
        rejects({"type": "paper", "ruling": "mm", "rows": 4, "cols": 30}, "шире колонки")

    def test_taller_than_the_limit(self) -> None:
        rejects({**PAPER, "rows": 80}, "слишком высокое")

    def test_lines_stretch_without_a_width(self) -> None:
        assert parse_visual(PAPER).cols is None

    def test_unknown_ruling(self) -> None:
        rejects({**PAPER, "ruling": "squared"}, "недопустимое значение")
