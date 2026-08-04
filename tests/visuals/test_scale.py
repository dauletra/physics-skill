"""The scale element: tick arithmetic and label thinning.

This is the shared machinery behind a ruler, a dial and a stopwatch, so the
rules it encodes — the limit is always numbered, labels land on round values,
an explicit `label_step` is obeyed — are tested here once instead of through
five instruments.
"""

from __future__ import annotations

import pytest

from physics_svg.draw import BBox, Pt
from physics_svg.elements import (
    ArcAxis,
    LinearAxis,
    division_count,
    division_values,
    hatch,
    label_every,
    liquid,
    nice_ticks,
    scale_marks,
    subdivisions,
    tick_layout,
    ticks_at,
)


class TestAxes:
    def test_linear_axis_runs_from_start_to_end(self) -> None:
        axis = LinearAxis(Pt(0, 10), Pt(100, 10), Pt(0, 1))
        assert axis.point(0) == Pt(0, 10)
        assert axis.point(0.5) == Pt(50, 10)
        assert axis.point(1) == Pt(100, 10)

    def test_linear_axis_normalises_the_tick_direction(self) -> None:
        axis = LinearAxis(Pt(0, 0), Pt(10, 0), Pt(0, 5))
        assert axis.outward(0) == Pt(0, 1)

    def test_column_axis_puts_the_minimum_at_the_bottom(self) -> None:
        axis = LinearAxis(Pt(0, 100), Pt(0, 20), Pt(1, 0))
        assert axis.point(0).y > axis.point(1).y

    def test_arc_axis_sweeps_between_the_angles(self) -> None:
        axis = ArcAxis(Pt(0, 0), 10, 150, 30)
        assert axis.angle(0) == 150
        assert axis.angle(0.5) == 90
        assert axis.point(0.5).y == pytest.approx(-10)

    def test_arc_ticks_point_away_from_the_centre(self) -> None:
        axis = ArcAxis(Pt(0, 0), 10, 180, 0)
        assert axis.outward(0.5).y == pytest.approx(-1)


class TestTickLayout:
    def test_one_tick_per_division_plus_the_end(self) -> None:
        ticks = tick_layout(0, 10, 1, max_labels=16)
        assert len(ticks) == 11
        assert ticks[0].value == 0 and ticks[-1].value == 10
        assert ticks[3].fraction == pytest.approx(0.3)

    def test_the_limit_of_the_scale_is_always_numbered(self) -> None:
        # Its measuring limit is read in every problem about ranges.
        ticks = tick_layout(0, 7, 1, max_labels=3)
        assert ticks[-1].labeled

    def test_a_label_too_close_to_the_limit_is_dropped(self) -> None:
        ticks = tick_layout(0, 11, 1, max_labels=4)
        labelled = [t.value for t in ticks if t.labeled]
        assert 11 in labelled
        assert 10 not in labelled

    def test_explicit_label_step_is_obeyed(self) -> None:
        ticks = tick_layout(0, 10, 0.5, max_labels=8, label_step=2)
        assert [t.value for t in ticks if t.labeled] == [0, 2, 4, 6, 8, 10]

    def test_labels_stay_within_the_limit(self) -> None:
        ticks = tick_layout(0, 100, 1, max_labels=6)
        assert sum(1 for t in ticks if t.labeled) <= 6

    def test_division_count(self) -> None:
        assert division_count(-20, 100, 2) == 60


class TestLabelThinning:
    def test_prefers_a_round_step_in_units_of_the_quantity(self) -> None:
        # 2.5 mm ticks are numbered every 5 mm (k=2), not every 2.5.
        assert label_every(2.5, 8, max_labels=16) == 2

    def test_a_round_step_beats_one_that_divides_evenly(self) -> None:
        # 12 divisions: k=3 and k=4 divide evenly, k=5 does not — but 5 is a
        # round number to read and 3 is not, so the numbers go 0, 5, 10, 12.
        assert label_every(1, 12, max_labels=5) == 5

    def test_falls_back_to_even_division_when_nothing_is_round(self) -> None:
        # Neither 9 nor 12 reads as a round step, so both k=3 and k=4 rank
        # only on dividing the scale evenly — and the denser one wins.
        assert label_every(3, 12, max_labels=5) == 3

    def test_never_exceeds_the_limit(self) -> None:
        for divisions in range(2, 60):
            k = label_every(1, divisions, max_labels=8)
            assert divisions // k + 1 <= 8


class TestContinuousTicks:
    def test_steps_are_one_two_or_five_times_a_power_of_ten(self) -> None:
        for low, high in [(0, 8), (0, 20), (250, 650), (0, 0.5), (-3, 3)]:
            ticks = nice_ticks(low, high)
            step = ticks[1] - ticks[0]
            mantissa = step / 10 ** int(round(__import__("math").log10(step)))
            assert round(mantissa, 6) in (0.1, 0.2, 0.5, 1, 2, 5, 10)

    def test_stays_inside_the_range(self) -> None:
        ticks = nice_ticks(250, 650)
        assert ticks[0] >= 250 and ticks[-1] <= 650

    def test_respects_the_tick_budget(self) -> None:
        assert len(nice_ticks(0, 1000, max_ticks=6)) <= 6

    def test_subdivisions_split_a_step_five_ways(self) -> None:
        ticks = nice_ticks(0, 10)
        minor = subdivisions(ticks, 0, 10)
        fine = (ticks[1] - ticks[0]) / 5
        assert all(abs(m / fine - round(m / fine)) < 1e-9 for m in minor)
        # Lines of the divisions themselves are drawn separately.
        assert not any(abs(m - t) < 1e-9 for m in minor for t in ticks)

    def test_subdivisions_cover_the_whole_range(self) -> None:
        # Outermost labelled ticks usually sit inside the range (240..660 is
        # numbered from 250), and the fine grid must not stop short of it.
        ticks = nice_ticks(240, 660)
        minor = subdivisions(ticks, 240, 660)
        assert min(minor) < ticks[0]
        assert max(minor) > ticks[-1]

    def test_subdivisions_of_a_degenerate_grid(self) -> None:
        assert subdivisions([5.0], 0, 10) == []


class TestPinnedDivisions:
    """Divisions an author pinned, as opposed to ones the renderer chose."""

    def test_counted_from_the_start_of_the_scale(self) -> None:
        assert division_values(0, 40, 5) == [0, 5, 10, 15, 20, 25, 30, 35, 40]

    def test_the_far_end_is_included(self) -> None:
        assert division_values(250, 650, 100)[-1] == 650

    def test_a_negative_start(self) -> None:
        assert division_values(-2, 2, 1) == [-2, -1, 0, 1, 2]

    def test_ticks_land_where_their_value_is(self) -> None:
        ticks = ticks_at([0, 5, 10], 0, 20)
        assert [tick.fraction for tick in ticks] == [0, 0.25, 0.5]

    def test_values_need_not_reach_the_ends(self) -> None:
        # A graph axis is numbered inside its own range: 300 on [250, 650]
        # sits an eighth of the way along, not at the very start.
        ticks = ticks_at(nice_ticks(250, 650), 250, 650)
        assert ticks[0].fraction == pytest.approx(0)
        assert all(0 <= tick.fraction <= 1 for tick in ticks)

    def test_every_kth_value_is_numbered(self) -> None:
        ticks = ticks_at(division_values(0, 40, 5), 0, 40, label_every=2)
        assert [tick.value for tick in ticks if tick.labeled] == [0, 10, 20, 30, 40]


class TestScaleMarks:
    def test_numbered_ticks_are_longer_and_carry_a_label(self) -> None:
        axis = LinearAxis(Pt(0, 0), Pt(100, 0), Pt(0, 1))
        nodes = scale_marks(
            axis, tick_layout(0, 10, 1, max_labels=16), major_length=9, minor_length=5,
            label_distance=17,
        )
        texts = [n for n in nodes if type(n).__name__ == "Text"]
        assert texts and all(t.at.y == 17 for t in texts)

    def test_labels_can_go_the_other_way_from_the_ticks(self) -> None:
        axis = LinearAxis(Pt(20, 100), Pt(20, 0), Pt(1, 0))
        nodes = scale_marks(
            axis, tick_layout(0, 4, 1, max_labels=8), major_length=9, minor_length=5,
            label_distance=3, label_direction=Pt(-1, 0), label_anchor="end",
        )
        texts = [n for n in nodes if type(n).__name__ == "Text"]
        assert all(t.at.x == 17 for t in texts)

    def test_skip_drops_a_tick(self) -> None:
        axis = ArcAxis(Pt(0, 0), 10, 90, -270)
        ticks = tick_layout(0, 4, 1, max_labels=12)
        full = scale_marks(axis, ticks, major_length=-7, minor_length=-4)
        skipped = scale_marks(axis, ticks, major_length=-7, minor_length=-4, skip=(0,))
        assert len(skipped) == len(full) - 1

    def test_without_a_label_distance_only_ticks_are_drawn(self) -> None:
        axis = LinearAxis(Pt(0, 0), Pt(10, 0), Pt(0, 1))
        nodes = scale_marks(axis, tick_layout(0, 2, 1, max_labels=8), major_length=5, minor_length=3)
        assert all(type(n).__name__ == "Line" for n in nodes)


class TestFills:
    def test_hatching_stays_inside_the_region(self) -> None:
        region = BBox(10, 20, 60, 40)
        for node in hatch(region):
            box = node.bbox()
            assert box is not None and region.expanded(1e-6).contains(box)

    def test_hatching_scales_with_the_area(self) -> None:
        assert len(hatch(BBox(0, 0, 100, 20))) > len(hatch(BBox(0, 0, 20, 20)))

    def test_liquid_lines_are_horizontal_and_inset(self) -> None:
        region = BBox(0, 0, 40, 20)
        for node in liquid(region):
            assert node.a.y == node.b.y
            assert node.a.x > region.x0 and node.b.x < region.x1

    def test_an_empty_region_gets_no_fill(self) -> None:
        assert hatch(BBox(0, 0, 0, 0)) == []
        assert liquid(BBox(0, 0, 10, 0)) == []
