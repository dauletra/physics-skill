"""Canvas: the computed viewBox and the scoped ids.

These two behaviours are why generators stop carrying magic numbers. The
viewBox test guards against clipping when a picture grows a label; the id
tests guard against the failure that made `<defs>` unusable before —
two instruments on one page defining the same id.
"""

import re
from dataclasses import replace

from physics_svg.draw import (
    BBox,
    Canvas,
    Circle,
    Group,
    Line,
    Pt,
    Rect,
    Style,
    Text,
    Transform,
    overlapping_labels,
)
from physics_svg.draw.canvas import SCREEN_SCALE


def viewbox_of(markup: str) -> tuple[float, ...]:
    match = re.search(r'viewBox="([^"]+)"', markup)
    assert match is not None
    return tuple(float(v) for v in match.group(1).split())


class TestViewBox:
    def test_fits_the_content_with_padding(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(10, 10), 20, 10))
        assert viewbox_of(canvas.render(padding=1)) == (9, 9, 22, 12)

    def test_labels_are_inside_the_box(self) -> None:
        canvas = Canvas()
        canvas.add(Circle(Pt(0, 0), 5), Text(Pt(0, 12), "очень длинная подпись", size=8))
        box = canvas.content_box()
        assert box is not None
        x0, y0, w, h = viewbox_of(canvas.render())
        assert BBox(x0, y0, x0 + w, y0 + h).contains(box)

    def test_explicit_viewbox_wins(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0, 0), 1, 1))
        assert viewbox_of(canvas.render(viewbox=BBox(0, 0, 100, 50))) == (0, 0, 100, 50)

    def test_empty_canvas_still_emits_valid_markup(self) -> None:
        assert viewbox_of(Canvas().render()) == (0, 0, 1, 1)
        assert Canvas().is_empty

    def test_bounds_are_snapped_so_estimates_do_not_churn_goldens(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0.13, 0.27), 5.31, 2.02))
        x0, y0, w, h = viewbox_of(canvas.render(padding=0))
        assert (x0 * 2) % 1 == 0 and (y0 * 2) % 1 == 0
        assert (w * 2) % 1 == 0 and (h * 2) % 1 == 0


class TestIdScoping:
    def test_unscoped_canvas_keeps_plain_ids(self) -> None:
        assert Canvas().uid("hatch") == "hatch"

    def test_scope_prefixes_every_id(self) -> None:
        assert Canvas("task-03-b").uid("hatch") == "task-03-b-hatch"

    def test_two_canvases_on_one_page_do_not_collide(self) -> None:
        first = Canvas("a").define("grid", lambda i: f'<pattern id="{i}"/>')
        second = Canvas("b").define("grid", lambda i: f'<pattern id="{i}"/>')
        assert first != second

    def test_definitions_are_emitted_once_and_reused(self) -> None:
        canvas = Canvas("p")
        first = canvas.define("grid", lambda i: f'<pattern id="{i}">one</pattern>')
        second = canvas.define("grid", lambda i: f'<pattern id="{i}">two</pattern>')
        markup = canvas.render()
        assert first == second == "p-grid"
        assert markup.count("<pattern") == 1
        assert "two" not in markup  # same name means same content, first wins

    def test_defs_block_appears_only_when_used(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0, 0), 1, 1))
        assert "<defs>" not in canvas.render()


class TestRendering:
    def test_document_mode_leaves_sizing_to_css(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0, 0), 10, 10))
        markup = canvas.render()
        assert 'class="visual-svg"' in markup
        assert "width=" not in markup.split(">")[0]

    def test_standalone_mode_carries_its_own_size_and_paper(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0, 0), 10, 10))
        markup = canvas.render(padding=0, sized=True, background="#fff")
        assert f'width="{10 * SCREEN_SCALE:g}"' in markup
        assert f'height="{10 * SCREEN_SCALE:g}"' in markup
        assert '<rect x="0" y="0" width="10" height="10" fill="#fff"/>' in markup

    def test_scale_multiplies_only_the_screen_size(self) -> None:
        canvas = Canvas()
        canvas.add(Rect(Pt(0, 0), 10, 10))
        markup = canvas.render(padding=0, sized=True, scale=SCREEN_SCALE * 2)
        assert 'width="30"' in markup
        assert 'viewBox="0 0 10 10"' in markup

    def test_fluid_mode_stretches_to_the_container(self) -> None:
        canvas = Canvas()
        canvas.add(Line(Pt(0, 0), Pt(100, 0), Style(stroke="#000", non_scaling=True)))
        markup = canvas.render(fluid_height=90)
        assert 'width="100%"' in markup
        assert 'height="90"' in markup
        assert 'preserveAspectRatio="none"' in markup
        assert 'vector-effect="non-scaling-stroke"' in markup

    def test_output_is_byte_stable(self) -> None:
        def build() -> str:
            canvas = Canvas("s")
            canvas.define("g", lambda i: f'<pattern id="{i}"/>')
            canvas.add(Circle(Pt(1 / 3, 2 / 3), 5), Text(Pt(0, 0), "υ₀"))
            return canvas.render()

        assert build() == build()


class TestOverlappingLabels:
    """The measure a crowded picture is reported by. It answers one question
    and changes nothing — a picture that is tight is still a picture."""

    def test_labels_apart_are_not_reported(self) -> None:
        canvas = Canvas()
        canvas.add(Text(Pt(0, 0), "10", size=9), Text(Pt(60, 0), "20", size=9))
        assert overlapping_labels(canvas) == []

    def test_labels_on_the_same_spot_are_reported_by_name(self) -> None:
        canvas = Canvas()
        canvas.add(Text(Pt(0, 0), "10", size=9), Text(Pt(2, 1), "20", size=9))
        assert overlapping_labels(canvas) == ["«10» и «20»"]

    def test_a_label_drawn_twice_is_one_label(self) -> None:
        """A graph prints every number twice — once as the white halo under
        it — and a number is not crowded by its own shadow."""
        canvas = Canvas()
        label = Text(Pt(0, 0), "10", size=9)
        canvas.add(replace(label, style=Style(fill="#fff", stroke="#fff", width=2)), label)
        assert overlapping_labels(canvas) == []

    def test_a_group_hides_nothing(self) -> None:
        canvas = Canvas()
        canvas.add(
            Group((Text(Pt(0, 0), "10", size=9),), Transform.translate(5, 0)),
            Text(Pt(6, 1), "20", size=9),
        )
        assert overlapping_labels(canvas) == ["«10» и «20»"]
