"""What a registered type must carry, checked for every type automatically.

This replaces the hand-kept checklist that used to live in the design notes.
A new illustration cannot be half-added: without example specs, without a
reference fragment for the model or without a gallery card for the teacher,
the suite fails. Nobody has to remember the list.
"""

from __future__ import annotations

import json
import re

import pytest

from physics_svg.draw import BBox, Canvas
from physics_svg.schema import SchemaError, emit_schema, spec_meta
from physics_svg.visuals import (
    build_svg,
    load_all,
    parse_visual,
    render_to_canvas,
    visual_annotation,
)

VIEWBOX = re.compile(r'viewBox="(-?[\d.]+) (-?[\d.]+) (-?[\d.]+) (-?[\d.]+)"')

#: Injected into every free-text field. If any of it reaches the markup
#: unescaped, a worksheet can carry active content.
PAYLOAD = '<script>alert("x")</script> & <sub>i</sub>'


class TestTypePackages:
    def test_has_example_specs(self, visual_type) -> None:
        assert visual_type.specs, f"у типа '{visual_type.tag}' нет ни одной спеки в specs/"

    def test_has_a_reference_fragment_for_the_model(self, visual_type) -> None:
        doc = visual_type.doc("doc.md")
        assert doc.exists(), f"нет {doc}"
        assert doc.read_text(encoding="utf-8").strip()

    def test_has_a_gallery_card_for_the_teacher(self, visual_type) -> None:
        card = visual_type.doc("card.md")
        assert card.exists(), f"нет {card}"
        assert card.read_text(encoding="utf-8").strip()

    def test_has_a_human_title(self, visual_type) -> None:
        assert visual_type.title and visual_type.title != visual_type.tag

    def test_spec_names_are_unique(self, visual_type) -> None:
        stems = [path.stem for path in visual_type.specs]
        assert len(set(stems)) == len(stems)

    def test_appears_in_the_published_schema(self, visual_type) -> None:
        schema = emit_schema({"visual": visual_annotation()})
        assert visual_type.model.__name__ in schema["$defs"]


class TestExamples:
    def test_parses(self, example) -> None:
        assert example.model is not None

    def test_renders(self, example) -> None:
        assert build_svg(example.model, scope="t").startswith("<svg")

    def test_frame_contains_everything_drawn(self, example) -> None:
        # A picture that outgrows its frame is silently clipped in a browser,
        # which is exactly the bug a computed viewBox exists to prevent.
        svg = build_svg(example.model, scope="t")
        match = VIEWBOX.search(svg)
        assert match is not None
        x0, y0, width, height = (float(v) for v in match.groups())
        frame = BBox(x0, y0, x0 + width, y0 + height)
        canvas = Canvas("t")
        render_to_canvas(example.model, canvas)
        content = canvas.content_box()
        assert content is not None
        assert frame.contains(content), f"{example.name}: содержимое {content} вне рамки {frame}"

    def test_output_is_deterministic(self, example) -> None:
        assert build_svg(example.model, scope="t") == build_svg(example.model, scope="t")

    def test_standalone_carries_its_own_paper_and_size(self, example) -> None:
        svg = build_svg(example.model, standalone=True)
        assert 'fill="#fff"' in svg
        assert "width=" in svg.split(">")[0]

    def test_author_text_is_escaped(self, example) -> None:
        """Every free-text field, one at a time, filled with markup."""
        injected = 0
        for key, value in example.raw.items():
            if not isinstance(value, str):
                continue
            try:
                model = parse_visual({**example.raw, key: PAYLOAD})
            except SchemaError:
                continue  # a closed vocabulary, not free text
            svg = build_svg(model, scope="t")
            assert "<script>" not in svg, f"{example.name}: поле '{key}' не экранировано"
            # Not every free-text field is drawn — a balance never prints its
            # unit, for instance — so appearing at all is not required, only
            # appearing escaped.
            injected += 1
        if injected == 0:
            pytest.skip("в спеке нет свободного текста")


class TestRegistry:
    def test_tags_match_the_spec_type_literal(self) -> None:
        for tag, entry in load_all().items():
            assert spec_meta(entry.model).tag == tag

    def test_every_spec_declares_its_type(self) -> None:
        for entry in load_all().values():
            for path in entry.specs:
                assert json.loads(path.read_text(encoding="utf-8"))["type"] == entry.tag
