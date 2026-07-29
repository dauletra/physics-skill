"""Vector diagrams: what the spec refuses, and whether the arithmetic holds.

The conformance suite already checks that every spec renders, fits its frame
and escapes author text. What is specific here is the geometry: a resultant
is *computed*, so it has to be computed correctly, and the arrangement rules
have to keep the picture readable.
"""

from __future__ import annotations

import math

import pytest

from physics_svg.draw import Pt
from physics_svg.elements import arrow, signed_angle_span, vector_sum
from physics_svg.schema import SchemaError
from physics_svg.visuals import build_svg, parse_visual
from physics_svg.visuals.vectors.model import VectorsSpec

BASE = {"type": "vectors", "vectors": [{"length": 3, "angle": 0}]}


def spec(**changes: object) -> dict:
    return {**BASE, **changes}


def rejects(data: dict, fragment: str) -> None:
    with pytest.raises(SchemaError) as info:
        parse_visual(data)
    assert fragment in str(info.value), f"ожидался фрагмент {fragment!r}, получено:\n{info.value}"


class TestArrowElement:
    def test_a_vector_is_a_line_and_a_head(self) -> None:
        nodes = arrow(Pt(0, 0), Pt(30, 0))
        assert len(nodes) == 2
        assert type(nodes[1]).__name__ == "Polyline"

    def test_the_line_stops_short_of_the_tip(self) -> None:
        # Otherwise the stroke thickens the point of the arrow.
        line = arrow(Pt(0, 0), Pt(30, 0))[0]
        assert line.b.x < 30

    def test_a_zero_length_vector_draws_nothing(self) -> None:
        assert arrow(Pt(5, 5), Pt(5, 5)) == []

    def test_the_head_fits_a_very_short_vector(self) -> None:
        nodes = arrow(Pt(0, 0), Pt(3, 0))
        assert nodes and all(node.bbox() is not None for node in nodes)


class TestVectorSum:
    def test_opposite_vectors_cancel(self) -> None:
        length, _ = vector_sum([(4, 0), (4, 180)])
        assert length == pytest.approx(0, abs=1e-9)

    def test_right_angle_sum(self) -> None:
        length, angle = vector_sum([(3, 0), (4, 90)])
        assert length == pytest.approx(5)
        assert angle == pytest.approx(math.degrees(math.atan2(4, 3)))

    def test_signed_span_takes_the_short_way(self) -> None:
        assert signed_angle_span(350, 10) == pytest.approx(20)
        assert signed_angle_span(10, 350) == pytest.approx(-20)


class TestResultant:
    def test_it_is_computed_from_the_vectors(self) -> None:
        model = parse_visual(
            spec(vectors=[{"length": 3, "angle": 0}, {"length": 4, "angle": 90}], resultant="R")
        )
        length, angle = model.sum
        assert length == pytest.approx(5)
        assert angle == pytest.approx(53.13, abs=0.01)

    def test_construction_lines_are_not_part_of_the_sum(self) -> None:
        # Dashed vectors are axes and projections, not forces.
        model = parse_visual(
            spec(
                vectors=[
                    {"length": 3, "angle": 0},
                    {"length": 9, "angle": 0, "style": "dashed"},
                ],
                resultant="R",
            )
        )
        assert model.sum[0] == pytest.approx(3)

    def test_a_vanishing_resultant_is_refused(self) -> None:
        rejects(
            spec(
                vectors=[{"length": 4, "angle": 0}, {"length": 4, "angle": 180}],
                resultant="R",
            ),
            "почти нулевая",
        )

    def test_balanced_forces_without_a_resultant_are_fine(self) -> None:
        model = parse_visual(
            spec(vectors=[{"length": 4, "angle": 90}, {"length": 4, "angle": -90}], body="block")
        )
        assert isinstance(model, VectorsSpec)


class TestArrangement:
    def test_a_parallelogram_takes_exactly_two(self) -> None:
        rejects(spec(arrangement="parallelogram"), "ровно два вектора")

    def test_a_body_only_belongs_at_a_common_origin(self) -> None:
        rejects(spec(arrangement="chain", body="block"), "только при arrangement 'common'")

    def test_a_chain_starts_each_vector_where_the_last_ended(self) -> None:
        from physics_svg.visuals.vectors.render import _place

        model = parse_visual(
            spec(arrangement="chain", vectors=[{"length": 3, "angle": 0}, {"length": 4, "angle": 90}])
        )
        placed = _place(model)
        assert placed[1].start == placed[0].end

    def test_a_common_origin_starts_every_vector_at_zero(self) -> None:
        from physics_svg.visuals.vectors.render import _place

        model = parse_visual(
            spec(vectors=[{"length": 3, "angle": 0}, {"length": 4, "angle": 90}])
        )
        assert {item.start for item in _place(model)} == {Pt(0.0, 0.0)}


class TestAngles:
    def test_a_mark_references_vectors_by_id(self) -> None:
        model = parse_visual(
            spec(
                vectors=[
                    {"length": 3, "angle": 0, "id": "a"},
                    {"length": 3, "angle": 60, "id": "b"},
                ],
                angles=[{"between": ["a", "b"], "label": "60°"}],
            )
        )
        assert "60°" in build_svg(model, scope="t")

    def test_an_unknown_id(self) -> None:
        rejects(
            spec(
                vectors=[{"length": 3, "angle": 0, "id": "a"}],
                angles=[{"between": ["a", "ghost"]}],
            ),
            "не найден",
        )

    def test_an_angle_with_itself(self) -> None:
        rejects(
            spec(
                vectors=[{"length": 3, "angle": 0, "id": "a"}],
                angles=[{"between": ["a", "a"]}],
            ),
            "между вектором и им же",
        )

    def test_duplicate_ids(self) -> None:
        rejects(
            spec(
                vectors=[
                    {"length": 3, "angle": 0, "id": "a"},
                    {"length": 3, "angle": 90, "id": "a"},
                ]
            ),
            "должны быть уникальны",
        )


class TestLimits:
    def test_length_is_counted_in_cells_so_it_stays_small(self) -> None:
        rejects(spec(vectors=[{"length": 40, "angle": 0}]), "должно быть не больше 12")

    def test_a_zero_length_vector(self) -> None:
        rejects(spec(vectors=[{"length": 0, "angle": 0}]), "должно быть больше 0")

    def test_too_many_vectors(self) -> None:
        rejects(
            spec(vectors=[{"length": 2, "angle": a * 40} for a in range(8)]),
            "не больше 6",
        )


class TestScale:
    def test_equal_numbers_draw_equal(self) -> None:
        from physics_svg.visuals.vectors.render import _cell_size, _place, _resultant

        model = parse_visual(
            spec(vectors=[{"length": 3, "angle": 0}, {"length": 3, "angle": 90}])
        )
        placed = _place(model)
        cell = _cell_size(placed, _resultant(model, placed))
        lengths = [(item.end - item.start).length() * cell for item in placed]
        assert lengths[0] == pytest.approx(lengths[1])

    def test_a_big_diagram_still_fits_the_target(self) -> None:
        from physics_svg.visuals.vectors.render import (
            MAX_CELL,
            MIN_CELL,
            _cell_size,
            _place,
            _resultant,
        )

        model = parse_visual(spec(vectors=[{"length": 12, "angle": 45}]))
        placed = _place(model)
        assert MIN_CELL <= _cell_size(placed, _resultant(model, placed)) <= MAX_CELL
