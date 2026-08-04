"""Graph divisions: who decides where the axis is ruled, ticked and numbered.

The conformance suite already checks that every spec renders and fits its
frame. What is specific here is the arithmetic of the scale — an author who
pins the division value is drawing a graph a student will read values off,
so "ticks every 5, numbers every 10" has to come out exactly that way.
"""

from __future__ import annotations

from physics_svg.draw import Line, Polyline, Text, num
from physics_svg.visuals import build_svg, parse_visual
from physics_svg.visuals.graph.model import PLOT_WIDTH, GraphSpec
from physics_svg.visuals.graph.render import _axes, axis_divisions

BASE = {
    "type": "graph",
    "x_label": "t, с",
    "y_label": "s, м",
    "x_range": [0, 40],
    "y_range": [0, 30],
}


def graph(**changes: object) -> GraphSpec:
    model = parse_visual({**BASE, **changes})
    assert isinstance(model, GraphSpec)
    return model


def values(ticks: object, *, labeled: bool) -> list[float]:
    return [tick.value for tick in ticks if tick.labeled is labeled]  # type: ignore[attr-defined]


class TestAxisDivisions:
    def test_nothing_pinned_numbers_every_division(self) -> None:
        ticks, fine = axis_divisions(0, 40, None, None, max_labels=13)
        assert values(ticks, labeled=True) == [0, 5, 10, 15, 20, 25, 30, 35, 40]
        assert values(ticks, labeled=False) == []
        # With no unnumbered division to rule, a fine grid needs invented ones.
        assert fine

    def test_both_pinned_are_obeyed(self) -> None:
        ticks, fine = axis_divisions(0, 40, 5, 10, max_labels=13)
        assert values(ticks, labeled=True) == [0, 10, 20, 30, 40]
        assert values(ticks, labeled=False) == [5, 15, 25, 35]
        # The unnumbered divisions are the fine grid — nothing to invent.
        assert fine == []

    def test_a_pinned_step_thins_its_own_numbers(self) -> None:
        ticks, _ = axis_divisions(0, 40, 1, None, max_labels=13)
        assert len(ticks) == 41
        assert values(ticks, labeled=True) == [0, 5, 10, 15, 20, 25, 30, 35, 40]

    def test_a_pinned_label_step_divides_the_axis_alone(self) -> None:
        ticks, _ = axis_divisions(0, 40, None, 20, max_labels=13)
        assert values(ticks, labeled=True) == [0, 20, 40]
        assert values(ticks, labeled=False) == []

    def test_the_renderers_own_choice_is_unchanged(self) -> None:
        # The auto path is what every existing document is drawn with.
        ticks, _ = axis_divisions(250, 650, None, None, max_labels=13)
        assert values(ticks, labeled=True)[:2] == [250, 300]


class TestAxes:
    """Everything about an axis lives outside the rectangle the data fills."""

    def test_the_quantities_stand_clear_of_the_plot(self) -> None:
        captions = [node for node in _axes(graph()) if isinstance(node, Text)]
        assert len(captions) == 2
        for caption in captions:
            box = caption.bbox()
            assert box is not None
            # Past the end of the x axis, or above the top of the y axis.
            assert box.x0 > PLOT_WIDTH or box.y1 < 0, caption.content

    def test_the_quantity_keeps_the_row_of_its_own_numbers(self) -> None:
        captions = {node.content: node for node in _axes(graph()) if isinstance(node, Text)}
        x_numbers = build_svg(graph(), scope="t")
        # Same baseline as the numbers under the x axis, same right edge as
        # the column beside the y axis.
        assert f'y="{num(captions["t, с"].at.y)}"' in x_numbers
        assert f'x="{num(captions["s, м"].at.x)}"' in x_numbers

    def test_each_axis_ends_in_an_arrow(self) -> None:
        heads = [node for node in _axes(graph()) if isinstance(node, Polyline)]
        assert len(heads) == 2

    def test_each_axis_runs_past_its_last_division(self) -> None:
        shafts = [node for node in _axes(graph()) if isinstance(node, Line)]
        assert max(shaft.b.x for shaft in shafts) > PLOT_WIDTH
        assert min(shaft.b.y for shaft in shafts) < 0


class TestGrid:
    def test_ticks_are_drawn_on_the_axes_either_way(self) -> None:
        for grid in ("none", "ticks", "fine"):
            svg = build_svg(graph(grid=grid, x_step=5, x_label_step=10), scope="t")
            # A tick is the only thing that reaches below the x axis.
            assert 'y2="96"' in svg, grid

    def test_a_numbered_tick_is_longer(self) -> None:
        svg = build_svg(graph(x_step=5, x_label_step=10), scope="t")
        assert svg.count('y2="96"') == 5
        assert svg.count('y2="94.5"') == 4

    def test_grid_none_rules_nothing(self) -> None:
        svg = build_svg(graph(grid="none"), scope="t")
        assert "#ccc" not in svg and "#e6e6e6" not in svg

    def test_unnumbered_divisions_are_ruled_only_by_a_fine_grid(self) -> None:
        pinned = {"x_step": 5, "x_label_step": 10, "y_step": 5, "y_label_step": 10}
        assert "#e6e6e6" not in build_svg(graph(**pinned), scope="t")
        assert "#e6e6e6" in build_svg(graph(grid="fine", **pinned), scope="t")
