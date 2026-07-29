"""Geometry is the layer every picture is built on: if a transform composes
in the wrong order or `polar` flips a sign, every illustration is subtly
wrong and no golden file can tell you why. These tests pin the conventions.
"""

import math

import pytest

from physics_svg.draw import BBox, Pt, Transform, angle_between, direction, polar, union_all
from physics_svg.draw.geometry import IDENTITY, ORIGIN


def approx(p: Pt) -> tuple[float, float]:
    return (pytest.approx(p.x, abs=1e-9), pytest.approx(p.y, abs=1e-9))


class TestPoint:
    def test_arithmetic(self) -> None:
        assert Pt(1, 2) + Pt(3, 4) == Pt(4, 6)
        assert Pt(3, 4) - Pt(1, 1) == Pt(2, 3)
        assert Pt(1, 2) * 3 == Pt(3, 6)
        assert 3 * Pt(1, 2) == Pt(3, 6)
        assert -Pt(1, -2) == Pt(-1, 2)

    def test_length_and_normalisation(self) -> None:
        assert Pt(3, 4).length() == 5
        assert Pt(0, 0).normalized() == Pt(0, 0)
        assert approx(Pt(3, 4).normalized()) == approx(Pt(0.6, 0.8))

    def test_angle_is_measured_the_textbook_way(self) -> None:
        # y grows downward on screen, so "up" is a negative y and +90 degrees.
        assert Pt(1, 0).angle() == pytest.approx(0)
        assert Pt(0, -1).angle() == pytest.approx(90)
        assert Pt(-1, 0).angle() == pytest.approx(180)

    def test_perpendicular_and_lerp(self) -> None:
        assert Pt(1, 0).perpendicular() == Pt(0, -1)
        assert Pt(0, 0).lerp(Pt(10, 20), 0.25) == Pt(2.5, 5.0)


class TestPolar:
    def test_zero_degrees_points_right(self) -> None:
        assert approx(polar(ORIGIN, 2, 0)) == approx(Pt(2, 0))

    def test_ninety_degrees_points_up_the_screen(self) -> None:
        assert approx(polar(ORIGIN, 2, 90)) == approx(Pt(0, -2))

    def test_respects_the_centre(self) -> None:
        assert approx(polar(Pt(10, 10), 5, 180)) == approx(Pt(5, 10))

    def test_direction_is_a_unit_vector(self) -> None:
        assert direction(37).length() == pytest.approx(1.0)

    def test_angle_between_is_signed_and_wraps(self) -> None:
        assert angle_between(Pt(1, 0), Pt(0, -1)) == pytest.approx(90)
        assert angle_between(Pt(0, -1), Pt(1, 0)) == pytest.approx(-90)
        assert abs(angle_between(Pt(1, 0), Pt(-1, 0))) == pytest.approx(180)


class TestBBox:
    def test_of_points(self) -> None:
        box = BBox.of([Pt(1, 5), Pt(-2, 3), Pt(4, 4)])
        assert box == BBox(-2, 3, 4, 5)

    def test_of_nothing_is_none(self) -> None:
        assert BBox.of([]) is None

    def test_union_and_expansion(self) -> None:
        box = BBox(0, 0, 1, 1).union(BBox(2, 2, 3, 3))
        assert box == BBox(0, 0, 3, 3)
        assert box.union(None) == box
        assert box.expanded(1) == BBox(-1, -1, 4, 4)

    def test_measurements(self) -> None:
        box = BBox(0, 0, 10, 4)
        assert (box.width, box.height) == (10, 4)
        assert box.center == Pt(5, 2)

    def test_contains(self) -> None:
        assert BBox(0, 0, 10, 10).contains(BBox(1, 1, 2, 2))
        assert not BBox(0, 0, 10, 10).contains(BBox(1, 1, 11, 2))

    def test_union_all_skips_empties(self) -> None:
        assert union_all([None, BBox(0, 0, 1, 1), None]) == BBox(0, 0, 1, 1)
        assert union_all([None, None]) is None


class TestTransform:
    def test_translate_and_scale(self) -> None:
        assert Transform.translate(3, 4).apply(Pt(1, 1)) == Pt(4, 5)
        assert Transform.scale(2).apply(Pt(1, 1)) == Pt(2, 2)
        assert Transform.scale(2, 3).apply(Pt(1, 1)) == Pt(2, 3)

    def test_rotation_is_counter_clockwise_on_screen(self) -> None:
        assert approx(Transform.rotate(90).apply(Pt(1, 0))) == approx(Pt(0, -1))

    def test_rotation_about_a_point(self) -> None:
        rotated = Transform.rotate(180, about=Pt(5, 5)).apply(Pt(6, 5))
        assert approx(rotated) == approx(Pt(4, 5))

    def test_then_applies_self_first(self) -> None:
        # Move right by 10, then scale by 2 -> (20, 0); the other order gives 12.
        combined = Transform.translate(10, 0).then(Transform.scale(2))
        assert approx(combined.apply(ORIGIN)) == approx(Pt(20, 0))
        other = Transform.scale(2).then(Transform.translate(10, 0))
        assert approx(other.apply(Pt(1, 0))) == approx(Pt(12, 0))

    def test_identity(self) -> None:
        assert IDENTITY.is_identity
        assert IDENTITY.apply(Pt(3, 7)) == Pt(3, 7)
        assert not Transform.translate(1, 0).is_identity

    def test_apply_box_uses_all_corners(self) -> None:
        box = Transform.rotate(90).apply_box(BBox(0, 0, 2, 1))
        assert box is not None
        assert (box.width, box.height) == (pytest.approx(1), pytest.approx(2))

    def test_apply_box_of_none(self) -> None:
        assert Transform.translate(1, 1).apply_box(None) is None

    def test_matches_manual_matrix_math(self) -> None:
        t = Transform.rotate(30).then(Transform.translate(5, -2))
        a = math.radians(-30)
        expected = Pt(
            math.cos(a) * 3 - math.sin(a) * 4 + 5,
            math.sin(a) * 3 + math.cos(a) * 4 - 2,
        )
        assert approx(t.apply(Pt(3, 4))) == approx(expected)
