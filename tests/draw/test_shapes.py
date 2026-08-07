"""The second serialiser of a drawing: nodes -> DrawingML.

The test that matters most here is the coverage one. A node with only `svg()`
would pass every other test in the suite and then fail in a teacher's Word,
so the rule is stated as a test: **every node kind is listed below, and every
one of them draws.** A new node breaks this test until its author gives it
both serialisers — which is the whole contract that keeps «one drawing, two
formats» true as the library grows.
"""

from __future__ import annotations

import math
import re

import pytest

from physics_svg.draw import BBox, Pt, Style, Transform
from physics_svg.draw.canvas import Canvas
from physics_svg.draw.nodes import (
    Circle,
    Ellipse,
    Group,
    Line,
    Node,
    Path,
    PathBuilder,
    Polyline,
    Raw,
    Rect,
    Text,
    Unsupported,
    arc,
)
from physics_svg.draw.pathdata import ArcTo, LineTo, Move, arc_geometry, parse, to_d
from physics_svg.draw.shapes import Drawing, Frame

FRAME = Frame(BBox(0, 0, 100, 100), 10000.0, 10000.0)

#: One of every node kind. The keys are checked against the class hierarchy,
#: so this dictionary cannot fall behind `draw/nodes.py`.
SAMPLES: dict[type, Node] = {
    Line: Line(Pt(0, 5), Pt(10, 5)),
    Polyline: Polyline((Pt(0, 0), Pt(5, 5), Pt(10, 0))),
    Rect: Rect(Pt(1, 1), 8, 4),
    Circle: Circle(Pt(5, 5), 3),
    Ellipse: Ellipse(Pt(5, 5), 4, 2),
    Path: PathBuilder().move(Pt(0, 0)).line(Pt(4, 4)).curve(Pt(5, 5), Pt(6, 6), Pt(7, 7)).build(),
    Text: Text(Pt(5, 5), "υ<sub>0</sub>, м/с"),
    Group: Group((Line(Pt(0, 0), Pt(1, 1)),), Transform.translate(3, 4)),
}


class TestCoverage:
    def test_every_node_kind_has_a_sample(self) -> None:
        # `Raw` is SVG-only by decision: arbitrary markup has no equivalent
        # among shapes, and a type that needs something new gets a node.
        kinds = {kind for kind in Node.__subclasses__() if kind is not Raw}
        assert kinds == set(SAMPLES), (
            "у узла нет перевода в фигуры Word: добавьте его в draw/shapes.py "
            "и образец в SAMPLES"
        )

    @pytest.mark.parametrize("kind", list(SAMPLES), ids=lambda k: k.__name__)
    def test_every_node_kind_draws(self, kind: type) -> None:
        xml = Drawing(FRAME).group([SAMPLES[kind]])
        assert "<wps:wsp>" in xml
        # Every shape needs an extent, and a zero one makes Word refuse the
        # whole document.
        for cx, cy in re.findall(r'<a:ext cx="(-?\d+)" cy="(-?\d+)"/>', xml):
            assert int(cx) > 0 and int(cy) > 0

    def test_raw_is_refused_with_a_way_out(self) -> None:
        with pytest.raises(Unsupported, match="заведи узел"):
            Raw("<circle/>").transformed(Transform.translate(1, 1))
        with pytest.raises(Unsupported, match="draw/shapes.py"):
            Drawing(FRAME).group([Raw("<circle/>")])


class TestTransforms:
    """Word has no nested frames, so a drawing is flattened into absolute
    geometry. These check the arithmetic that does it."""

    def test_a_point_follows_the_matrix(self) -> None:
        t = Transform.translate(2, 3).then(Transform.scale(2))
        assert Line(Pt(1, 1), Pt(2, 2)).transformed(t).a == t.apply(Pt(1, 1))

    def test_a_group_flattens_into_absolute_children(self) -> None:
        inner = Group((Line(Pt(0, 0), Pt(1, 0)),), Transform.translate(10, 0))
        outer = Group((inner,), Transform.translate(0, 5))
        flat = outer.flattened()
        assert len(flat) == 1
        assert isinstance(flat[0], Line)
        assert flat[0].a == Pt(10, 5) and flat[0].b == Pt(11, 5)

    def test_a_flattened_group_stays_inside_the_frame_it_was_measured_by(self) -> None:
        """The picture's frame is computed from the unflattened tree, and the
        shapes are drawn from the flattened one. If the second could stick out
        of the first, a turned element would be clipped in Word.

        Not equality: `Group.bbox()` turns the children's box, which is a
        conservative estimate of the box of the turned children.
        """
        group = Group(
            (Circle(Pt(0, 0), 2), Rect(Pt(1, 1), 4, 4)),
            Transform.rotate(30).then(Transform.translate(7, 3)),
        )
        flat = BBox.of(
            point
            for node in group.flattened()
            for box in [node.bbox()]
            if box is not None
            for point in box.corners
        )
        frame = group.bbox()
        assert flat is not None and frame is not None
        assert frame.contains(flat, tolerance=1e-6)

    def test_a_turned_rectangle_becomes_its_corners(self) -> None:
        turned = Rect(Pt(0, 0), 4, 2).transformed(Transform.rotate(45))
        assert isinstance(turned, Polyline) and turned.closed

    def test_a_stretched_circle_becomes_an_ellipse(self) -> None:
        stretched = Circle(Pt(0, 0), 3).transformed(Transform.scale(2, 1))
        assert isinstance(stretched, Ellipse)
        assert (stretched.rx, stretched.ry) == (6, 3)

    def test_a_stretched_label_is_refused(self) -> None:
        # Half the letters would be wider than the other half.
        with pytest.raises(Unsupported, match="подпись"):
            Text(Pt(0, 0), "υ").transformed(Transform.scale(2, 1))

    def test_a_stretched_ruling_keeps_its_line_weight(self) -> None:
        # `non_scaling` is the whole reason a stretched field does not turn
        # one side of its frame into a thread.
        style = Style(stroke="#000", width=1.0, non_scaling=True)
        stretched = Line(Pt(0, 0), Pt(1, 0), style).transformed(Transform.scale(4, 1))
        assert stretched.style.width == 1.0

    def test_an_arc_survives_a_shift_and_is_sampled_otherwise(self) -> None:
        curved = arc(Pt(0, 0), 5, 0, 90)
        shifted = curved.transformed(Transform.translate(3, 3))
        assert any(isinstance(s, ArcTo) for s in shifted.segments())
        turned = curved.transformed(Transform.rotate(30))
        assert all(not isinstance(s, ArcTo) for s in turned.segments())
        assert sum(isinstance(s, LineTo) for s in turned.segments()) > 5


class TestPathData:
    def test_a_path_round_trips(self) -> None:
        d = "M0,0 L4,4 C5,5 6,6 7,7 Z"
        assert to_d(parse(d)) == d

    def test_extra_numbers_repeat_the_command(self) -> None:
        # How the ruling tiles are written: `M12 0 L0 0 0 12`.
        segments = parse("M12 0 L0 0 0 12")
        assert [type(s) for s in segments] == [Move, LineTo, LineTo]
        assert segments[2].to == Pt(0, 12)

    def test_a_quarter_arc_knows_its_centre(self) -> None:
        geometry = arc_geometry(Pt(5, 0), ArcTo(5.0, 0, 0, Pt(0, -5)))
        assert math.isclose(geometry.center.x, 0, abs_tol=1e-9)
        assert math.isclose(geometry.center.y, 0, abs_tol=1e-9)
        assert math.isclose(abs(geometry.sweep_deg), 90, abs_tol=1e-6)

    def test_relative_commands_are_refused(self) -> None:
        # The library never emits them; silently misreading one would move a
        # whole picture.
        with pytest.raises(ValueError, match="относительная"):
            parse("M0,0 l4,4")


class TestTiling:
    """A ruling is declared once and rendered twice: as a pattern for SVG, as
    lines for shapes."""

    def test_a_cell_edge_becomes_one_line_across_the_field(self) -> None:
        # Repeating the cell literally would be quadratic — six thousand
        # shapes for a millimetre field instead of a few hundred lines.
        canvas = Canvas()
        cell = canvas.tiling("grid", 10, 10, [Path("M10 0 L0 0 0 10", Style(stroke="#000"))])
        nodes = cell.expanded(BBox(0, 0, 100, 50))
        assert all(isinstance(node, Line) for node in nodes)
        assert len(nodes) == 5 + 10  # rows of horizontals, columns of verticals

    def test_what_is_not_an_edge_is_repeated_cell_by_cell(self) -> None:
        canvas = Canvas()
        dots = canvas.tiling("dots", 10, 10, [Circle(Pt(5, 5), 1)])
        assert len(dots.expanded(BBox(0, 0, 30, 20))) == 3 * 2

    def test_a_tiling_over_a_tiling_expands_both(self) -> None:
        canvas = Canvas()
        fine = canvas.tiling("fine", 5, 5, [Path("M5 0 L0 0 0 5", Style(stroke="#eee"))])
        coarse = canvas.tiling(
            "coarse", 10, 10, [Path("M10 0 L0 0 0 10", Style(stroke="#000"))], base=fine
        )
        nodes = coarse.expanded(BBox(0, 0, 20, 20))
        assert len(nodes) == (4 + 4) + (2 + 2)

    def test_a_filled_area_becomes_lines_for_the_shapes_backend(self) -> None:
        canvas = Canvas("v1")
        cell = canvas.tiling("grid", 10, 10, [Path("M10 0 L0 0 0 10", Style(stroke="#000"))])
        canvas.add(canvas.fill_tiled(BBox(0, 0, 20, 20), cell))
        assert all(isinstance(node, Line) for node in canvas.flat_nodes())
        # …while the SVG still fills one rectangle with one pattern.
        assert 'fill="url(#v1-grid)"' in canvas.render()
        assert "<pattern id=\"v1-grid\"" in canvas.render()
