"""Properties every slide kind must have, checked for all of them at once.

Written against the registry, so a new slide kind is covered the moment its
module exists. The escaping fuzz through the JSON gate arrives with the
emitter (П3); until then the promise checked here is the schema's: the
documented examples validate, the envelope is standard, and the reference
carries both of its audiences' texts.
"""

from __future__ import annotations

import pytest

from physics_svg.presentation import parse_slide
from physics_svg.presentation.slides import load_all, slide_annotation
from physics_svg.schema import SchemaError, emit_schema, spec_meta

KINDS = list(load_all().values())
EACH_KIND = pytest.mark.parametrize("kind", KINDS, ids=[k.tag for k in KINDS])


@EACH_KIND
class TestRegistry:
    def test_tag_matches_the_spec_literal(self, kind) -> None:
        assert spec_meta(kind.model).tag == kind.tag

    def test_has_a_reference_fragment_for_the_model(self, kind) -> None:
        assert kind.doc.exists(), f"нет {kind.doc}"
        assert kind.doc.read_text(encoding="utf-8").strip()

    def test_has_a_card_for_the_teacher(self, kind) -> None:
        # Two audiences, two texts: the card feeds the site, the fragment
        # feeds the bundle.
        assert kind.card.exists(), f"нет {kind.card}"
        text = kind.card.read_text(encoding="utf-8")
        assert text.strip().startswith("# ")
        assert "Что сказать Claude" in text, "в карточке нет примеров фраз для учителя"

    def test_has_a_human_title(self, kind) -> None:
        assert kind.title and kind.title != kind.tag

    def test_appears_in_the_published_schema(self, kind) -> None:
        schema = emit_schema({"slide": slide_annotation()})
        assert kind.model.__name__ in schema["$defs"]

    def test_carries_the_standard_envelope(self, kind) -> None:
        # A slide's number is its position in the manifest order; numbering
        # and layout must not leak into the payload.
        fields = spec_meta(kind.model).fields
        assert "id" in fields
        assert "label" not in fields

    def test_has_a_place_in_the_reading_order(self, kind) -> None:
        orders = [entry.order for entry in load_all().values()]
        assert orders == sorted(orders) and len(set(orders)) == len(orders)


@EACH_KIND
class TestDocumentedExample:
    def test_every_documented_example_is_a_valid_slide(self, kind) -> None:
        # A whole slide, not a bare fragment: the slide is the smallest
        # thing that validates and the smallest thing the player shows.
        for slide in kind.examples:
            assert slide.get("type") == kind.tag, f"пример '{kind.tag}' — не этот слайд"
            assert parse_slide(slide, "s") is not None


class TestInvariants:
    def test_an_unknown_type_is_refused_with_the_known_ones(self) -> None:
        with pytest.raises(SchemaError):
            parse_slide({"type": "karaoke"}, "s")

    def test_a_content_slide_cannot_be_a_bare_heading(self) -> None:
        # A heading alone announces content that never comes (principle 8).
        with pytest.raises(SchemaError, match="пуст"):
            parse_slide({"type": "content", "heading": "Скорость"}, "s")

    def test_a_visual_is_validated_with_the_visual_schema(self) -> None:
        # The union comes from the visual registry: a broken graph inside a
        # slide fails like a broken graph anywhere else, with a path.
        with pytest.raises(SchemaError):
            parse_slide(
                {"type": "board_task", "text": "Найдите путь.", "visual": {"type": "graph"}},
                "s",
            )
