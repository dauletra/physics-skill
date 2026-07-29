"""Primitives: markup shape, extent reporting, and the escaping guarantee.

The escaping tests matter most. A generator that formats `<text>` by hand can
forget to escape author input exactly once and ship an XSS-shaped bug in a
worksheet; `Text` escapes what it is handed, so there is nothing to forget.
"""

import pytest

from physics_svg.draw import (
    BBox,
    Circle,
    Group,
    Line,
    PathBuilder,
    Polyline,
    Pt,
    Raw,
    Rect,
    Style,
    Text,
    Transform,
    arc,
)


class TestSimpleShapes:
    def test_line(self) -> None:
        node = Line(Pt(0, 0), Pt(10, 5))
        assert 'x1="0" y1="0" x2="10" y2="5"' in node.svg()
        assert node.bbox() == BBox(0, 0, 10, 5)

    def test_numbers_are_trimmed_not_padded(self) -> None:
        assert 'x1="0.5"' in Line(Pt(0.5, 1.0), Pt(2.25, 3.999)).svg()
        assert 'y1="1"' in Line(Pt(0.5, 1.0), Pt(2.25, 3.999)).svg()

    def test_polyline_closes_into_a_polygon(self) -> None:
        points = (Pt(0, 0), Pt(4, 0), Pt(4, 3))
        assert Polyline(points).svg().startswith("<polyline")
        assert Polyline(points, closed=True).svg().startswith("<polygon")
        assert Polyline(points).bbox() == BBox(0, 0, 4, 3)

    def test_rect(self) -> None:
        node = Rect(Pt(1, 2), 10, 4, radius=2)
        assert 'rx="2"' in node.svg()
        assert node.bbox() == BBox(1, 2, 11, 6)

    def test_circle(self) -> None:
        assert Circle(Pt(5, 5), 3).bbox() == BBox(2, 2, 8, 8)

    def test_style_attributes_are_emitted(self) -> None:
        markup = Line(Pt(0, 0), Pt(1, 1), Style(stroke="#000", width=1.5, dash="8,4")).svg()
        assert 'stroke="#000"' in markup
        assert 'stroke-width="1.5"' in markup
        assert 'stroke-dasharray="8,4"' in markup


class TestText:
    def test_escapes_author_markup(self) -> None:
        markup = Text(Pt(0, 0), '<script>alert("x")</script>').svg()
        assert "<script>" not in markup
        assert "&lt;script&gt;" in markup

    def test_keeps_sup_and_sub_as_tspans(self) -> None:
        markup = Text(Pt(0, 0), "м/с<sup>2</sup>", size=10).svg()
        assert '<tspan baseline-shift="super"' in markup
        assert "</tspan>" in markup
        # Nested size follows the parent size instead of being hard-coded.
        assert 'font-size="7.2"' in markup

    def test_anchor_shifts_the_extent(self) -> None:
        start = Text(Pt(0, 0), "12", anchor="start").bbox()
        middle = Text(Pt(0, 0), "12", anchor="middle").bbox()
        end = Text(Pt(0, 0), "12", anchor="end").bbox()
        assert start is not None and middle is not None and end is not None
        assert start.x0 == 0
        assert middle.x0 == pytest.approx(-start.width / 2)
        assert end.x1 == pytest.approx(0)

    def test_rotation_swaps_the_extent(self) -> None:
        upright = Text(Pt(0, 0), "скорость").bbox()
        turned = Text(Pt(0, 0), "скорость", rotate=90).bbox()
        assert upright is not None and turned is not None
        assert turned.height == pytest.approx(upright.width)

    def test_rotation_is_emitted_clockwise_for_svg(self) -> None:
        # SVG rotates clockwise for positive angles; a textbook +90 must
        # therefore come out as -90 in the attribute.
        assert 'transform="rotate(-90 0 0)"' in Text(Pt(0, 0), "υ", rotate=90).svg()


class TestGroup:
    def test_transform_is_emitted_as_a_matrix(self) -> None:
        group = Group((Line(Pt(0, 0), Pt(1, 0)),), Transform.translate(5, 6))
        assert 'transform="matrix(1 0 0 1 5 6)"' in group.svg()

    def test_identity_transform_is_omitted(self) -> None:
        assert "transform" not in Group((Line(Pt(0, 0), Pt(1, 0)),)).svg()

    def test_extent_is_reported_in_parent_coordinates(self) -> None:
        group = Group((Rect(Pt(0, 0), 2, 2),), Transform.translate(10, 10))
        assert group.bbox() == BBox(10, 10, 12, 12)

    def test_nested_groups_compose(self) -> None:
        inner = Group((Rect(Pt(0, 0), 2, 2),), Transform.translate(1, 1))
        outer = Group((inner,), Transform.scale(2))
        assert outer.bbox() == BBox(2, 2, 6, 6)

    def test_empty_group_has_no_extent(self) -> None:
        assert Group(()).bbox() is None


class TestArcsAndPaths:
    def test_arc_extent_covers_the_sweep_not_just_the_ends(self) -> None:
        # A half-circle from 0 to 180 degrees must include the top of the arc.
        box = arc(Pt(0, 0), 10, 0, 180).bbox()
        assert box is not None
        assert box.y0 == pytest.approx(-10, abs=0.02)
        assert box.x0 == pytest.approx(-10)
        assert box.x1 == pytest.approx(10)

    def test_arc_sets_the_sweep_flag_for_screen_orientation(self) -> None:
        assert "0 0 0 " in arc(Pt(0, 0), 5, 0, 90).d  # counter-clockwise
        assert "0 0 1 " in arc(Pt(0, 0), 5, 90, 0).d  # clockwise

    def test_large_arc_flag(self) -> None:
        assert " 1 " in arc(Pt(0, 0), 5, 0, 270).d

    def test_path_builder_records_extent(self) -> None:
        path = PathBuilder().move(Pt(0, 0)).line(Pt(10, 0)).line(Pt(10, 5)).close().build()
        assert path.d == "M0,0 L10,0 L10,5 Z"
        assert path.bbox() == BBox(0, 0, 10, 5)

    def test_path_builder_arc_moves_first_when_empty(self) -> None:
        path = PathBuilder().arc(Pt(0, 0), 4, 0, 90).build()
        assert path.d.startswith("M4,0 A4,4")

    def test_curve_extent_uses_the_control_hull(self) -> None:
        path = PathBuilder().move(Pt(0, 0)).curve(Pt(0, -10), Pt(10, -10), Pt(10, 0)).build()
        box = path.bbox()
        assert box is not None
        assert box.y0 == -10


class TestRaw:
    def test_markup_passes_through_and_may_be_extentless(self) -> None:
        node = Raw("<pattern id='p'/>")
        assert node.svg() == "<pattern id='p'/>"
        assert node.bbox() is None
