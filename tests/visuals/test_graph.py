"""Graph divisions: who decides where the axis is ruled, ticked and numbered.

The conformance suite already checks that every spec renders and fits its
frame. What is specific here is the arithmetic of the scale — an author who
pins the division value is drawing a graph a student will read values off,
so "ticks every 5, numbers every 10" has to come out exactly that way.
"""

from __future__ import annotations

from library import EXAMPLES
from physics_svg.draw import (
    BOARD,
    GRID,
    GRID_FINE,
    SHEET,
    Canvas,
    Line,
    Medium,
    Polyline,
    Pt,
    Text,
    num,
)
from physics_svg.visuals import build_svg, parse_visual
from physics_svg.visuals.graph.model import (
    MIN_LABEL_GAP_Y,
    PLOT_HEIGHT,
    PLOT_WIDTH,
    GraphSpec,
)
from physics_svg.visuals.graph.render import (
    _LABEL_CLEARANCE_X,
    _LABEL_CLEARANCE_Y,
    _LABEL_DISTANCE_X,
    _axes,
    _number_every,
    axis_divisions,
    label_budget,
)
from physics_svg.visuals.registry import render_to_canvas


def budget_x(medium: Medium) -> int:
    return label_budget(PLOT_WIDTH, _LABEL_CLEARANCE_X * medium.number)


def budget_y(medium: Medium) -> int:
    return label_budget(PLOT_HEIGHT, _LABEL_CLEARANCE_Y * medium.number)

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
    def test_nothing_pinned_numbers_what_fits(self) -> None:
        ticks, fine = axis_divisions(0, 40, None, None, max_labels=13)
        assert values(ticks, labeled=True) == [0, 5, 10, 15, 20, 25, 30, 35, 40]
        assert values(ticks, labeled=False) == []
        # With no unnumbered division to rule, a fine grid needs invented ones.
        assert fine

    def test_a_tight_budget_thins_the_numbers_and_keeps_the_divisions(self) -> None:
        """The same range, numbered as sparsely as the y axis needs it.

        The divisions do not move: an unnumbered one keeps its tick, and a
        student counts cells by them.
        """
        ticks, fine = axis_divisions(0, 40, None, None, max_labels=7)
        assert values(ticks, labeled=True) == [0, 10, 20, 30, 40]
        assert values(ticks, labeled=False) == [5, 15, 25, 35]
        assert [tick.value for tick in ticks] == [0, 5, 10, 15, 20, 25, 30, 35, 40]
        # There are unnumbered divisions now, so a fine grid rules those
        # instead of inventing a finer step.
        assert fine == []

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


CORNER = Pt(0, PLOT_HEIGHT)

#: Both ranges spanning zero: a coordinate plane, not a framed chart.
QUADRANTS = {"x_range": [-4, 4], "y_range": [-8, 8]}


class TestAxes:
    """Everything about an axis lives outside the rectangle the data fills."""

    def test_the_quantities_stand_clear_of_the_plot(self) -> None:
        captions = [node for node in _axes(graph(), CORNER, SHEET) if isinstance(node, Text)]
        assert len(captions) == 2
        for caption in captions:
            box = caption.bbox()
            assert box is not None
            # Past the end of the x axis, or above the top of the y axis.
            assert box.x0 > PLOT_WIDTH or box.y1 < 0, caption.content

    def test_the_quantity_keeps_the_row_of_its_own_numbers(self) -> None:
        captions = {
            node.content: node for node in _axes(graph(), CORNER, SHEET) if isinstance(node, Text)
        }
        x_numbers = build_svg(graph(), scope="t")
        # Same baseline as the numbers under the x axis, same right edge as
        # the column beside the y axis.
        assert f'y="{num(captions["t, с"].at.y)}"' in x_numbers
        assert f'x="{num(captions["s, м"].at.x)}"' in x_numbers

    def test_each_axis_ends_in_an_arrow(self) -> None:
        heads = [node for node in _axes(graph(), CORNER, SHEET) if isinstance(node, Polyline)]
        assert len(heads) == 2

    def test_each_axis_runs_past_its_last_division(self) -> None:
        shafts = [node for node in _axes(graph(), CORNER, SHEET) if isinstance(node, Line)]
        assert max(shaft.b.x for shaft in shafts) > PLOT_WIDTH
        assert min(shaft.b.y for shaft in shafts) < 0


class TestLabelDensity:
    """Numbers stack up the y axis and stand apart along the x axis, so the
    two axes cannot share one budget — and neither can two media."""

    def test_the_vertical_budget_is_the_tighter_one(self) -> None:
        assert budget_y(SHEET) < budget_x(SHEET)

    def test_the_sheet_is_numbered_exactly_as_it_always_was(self) -> None:
        """Nine along x and seven down y: the counts the library was drawn
        with, now arrived at from the label height instead of written down."""
        assert (budget_x(SHEET), budget_y(SHEET)) == (9, 7)

    def test_a_bigger_number_gets_fewer_of_its_own(self) -> None:
        """The point of the whole budget: numbers do not multiply as they
        grow. At the board step the axes hold six and five
        (docs/visual-scale.md §6.4)."""
        assert (budget_x(BOARD), budget_y(BOARD)) == (6, 5)

    def test_numbers_down_the_y_axis_keep_their_air(self) -> None:
        """Every case in the library, measured: a number and the next one.

        Half a line of white between them is the point of the budget; the
        assertion is on the gap, not on a count, so a new spec is covered.
        """
        for example in EXAMPLES:
            if example.type.tag != "graph":
                continue
            model = example.model
            ticks, _ = axis_divisions(
                *model.y_range, model.y_step, model.y_label_step, budget_y(SHEET)
            )
            numbered = sum(1 for tick in ticks if tick.labeled)
            gap = PLOT_HEIGHT / (numbered - 1)
            assert gap >= MIN_LABEL_GAP_Y, f"{example.name}: {numbered} подписей, шаг {gap:.1f}"

    def test_the_horizontal_choice_is_untouched(self) -> None:
        # The x axis was never crowded; these are the counts it has always had.
        for (low, high), expected in {(0, 6): 7, (0, 10): 6, (250, 650): 9}.items():
            ticks, _ = axis_divisions(low, high, None, None, budget_x(SHEET))
            assert sum(1 for tick in ticks if tick.labeled) == expected

    def test_a_pinned_step_is_numbered_the_same_on_both_media(self) -> None:
        """The author's step is the question, not a suggestion: a slide that
        quietly numbered half as often would be asking something else."""
        ticks, _ = axis_divisions(0, 40, 2.0, 4.0, budget_x(SHEET))
        assert sum(1 for tick in ticks if tick.labeled) == 11  # more than a board holds
        assert _number_every(ticks, 4.0, budget_x(BOARD)) == 1
        assert _number_every(ticks, None, budget_x(BOARD)) > 1


class TestTheRulingIsNotTheNumbering:
    """A student counts cells and reads off the heavy line — so the ruling is
    the task, and the task cannot differ between paper and a board. Only how
    many of the divisions say their value out loud may give way to a larger
    label (docs/visual-scale.md §3.5)."""

    def each_medium(self, model: object) -> list[tuple[list[str], int]]:
        drawn = []
        for medium in (SHEET, BOARD):
            canvas = Canvas(medium=medium)
            render_to_canvas(model, canvas)
            nodes = canvas.flat_nodes()
            drawn.append(
                (
                    [
                        f"{n.style.stroke} {n.a.x:.2f} {n.a.y:.2f} {n.b.x:.2f} {n.b.y:.2f}"
                        for n in nodes
                        if isinstance(n, Line) and n.style in (GRID, GRID_FINE)
                    ],
                    sum(1 for n in nodes if isinstance(n, Text)),
                )
            )
        return drawn

    def test_the_grid_is_the_same_picture_on_both_media(self) -> None:
        for example in EXAMPLES:
            if example.type.tag != "graph":
                continue
            sheet, board = self.each_medium(example.model)
            assert sheet[0] == board[0], f"{example.name}: сетка разошлась"

    def test_a_board_prints_no_more_numbers_than_a_sheet(self) -> None:
        for example in EXAMPLES:
            if example.type.tag != "graph":
                continue
            sheet, board = self.each_medium(example.model)
            assert board[1] <= sheet[1], example.name


class TestSharedZero:
    def test_the_origin_is_numbered_once(self) -> None:
        svg = build_svg(graph(), scope="t")
        assert svg.count(">0</text>") == 2  # one number, one white halo under it

    def test_a_corner_that_is_not_the_origin_keeps_both_numbers(self) -> None:
        svg = build_svg(graph(x_range=[250, 650], y_range=[0, 250]), scope="t")
        assert ">250</text>" in svg and ">0</text>" in svg


class TestNegativeRanges:
    """A range that spans zero makes a coordinate plane: the axes cross at the
    origin instead of framing the data from the outside."""

    def test_the_axes_cross_at_the_origin(self) -> None:
        svg = build_svg(graph(**QUADRANTS), scope="t")
        # Midway across and midway down: x = 0 and y = 0 sit in the middle of
        # both ranges, and the heavy lines are drawn there.
        assert f'x1="{num(PLOT_WIDTH / 2)}" y1="{num(PLOT_HEIGHT)}"' in svg
        assert f'x1="0" y1="{num(PLOT_HEIGHT / 2)}"' in svg

    def test_the_edges_carry_no_axis(self) -> None:
        # The old picture drew the x axis along the bottom of the plot, which
        # for these ranges is the line F = -8 Н, not the abscissa.
        heavy = _heavy_lines(graph(**QUADRANTS))
        assert all(line.a.y != PLOT_HEIGHT or line.b.y != PLOT_HEIGHT for line in heavy)

    def test_a_range_starting_at_zero_is_drawn_as_before(self) -> None:
        heavy = _heavy_lines(graph())
        assert any(line.a.y == line.b.y == PLOT_HEIGHT for line in heavy)
        assert any(line.a.x == line.b.x == 0 for line in heavy)

    def test_a_range_that_never_reaches_zero_keeps_its_axes_at_the_edges(self) -> None:
        # Both scales starting away from zero (250 К, 90 кПа): there is no
        # origin inside the plot to move the axes to.
        model = graph(
            x_range=[250, 400], x_step=10, x_label_step=50,
            y_range=[90, 160], y_step=5, y_label_step=10,
        )
        svg = build_svg(model, scope="t")
        assert f'x1="0" y1="{num(PLOT_HEIGHT)}" x2="{num(PLOT_WIDTH)}"' in svg
        # The first number at the corner is the start of the range, not zero.
        assert ">250</text>" in svg and ">90</text>" in svg
        assert ">0</text>" not in svg

    def test_the_numbers_follow_their_axis(self) -> None:
        svg = build_svg(graph(**QUADRANTS), scope="t")
        # Negative numbers are printed, and the row of x numbers sits under
        # the axis in the middle, not under the bottom edge of the plot.
        assert ">-4</text>" in svg and ">-8</text>" in svg
        assert f'y="{num(PLOT_HEIGHT / 2 + _LABEL_DISTANCE_X * SHEET.number)}"' in svg


def _heavy_lines(model: GraphSpec) -> list[Line]:
    corner = Pt(
        PLOT_WIDTH / 2 if model.x_range[0] < 0 else 0.0,
        PLOT_HEIGHT / 2 if model.y_range[0] < 0 else PLOT_HEIGHT,
    )
    return [node for node in _axes(model, corner, SHEET) if isinstance(node, Line)]


class TestGrid:
    def test_ticks_are_drawn_on_the_axes_either_way(self) -> None:
        for grid in ("none", "ticks", "fine"):
            svg = build_svg(graph(grid=grid, x_step=5, x_label_step=10), scope="t")
            # A tick is the only thing that reaches below the x axis.
            assert 'y2="96"' in svg, grid

    def test_a_numbered_tick_is_longer(self) -> None:
        svg = build_svg(graph(x_step=5, x_label_step=10), scope="t")
        # Four of the five numbered divisions: the one at the origin is left
        # to the y axis, which stands on it.
        assert svg.count('y2="96"') == 4
        assert svg.count('y2="94.5"') == 4

    def test_grid_none_rules_nothing(self) -> None:
        svg = build_svg(graph(grid="none"), scope="t")
        assert "#ccc" not in svg and "#e6e6e6" not in svg

    def test_unnumbered_divisions_are_ruled_only_by_a_fine_grid(self) -> None:
        pinned = {"x_step": 5, "x_label_step": 10, "y_step": 5, "y_label_step": 10}
        assert "#e6e6e6" not in build_svg(graph(**pinned), scope="t")
        assert "#e6e6e6" in build_svg(graph(grid="fine", **pinned), scope="t")
