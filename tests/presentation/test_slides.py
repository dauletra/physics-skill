"""Properties every slide kind must have, checked for all of them at once.

Written against the registry, so a new slide kind is covered the moment its
module exists. The escaping fuzz through the JSON gate arrives with the
emitter (П3); until then the promise checked here is the schema's: the
documented examples validate, the envelope is standard, and the reference
carries both of its audiences' texts.
"""

from __future__ import annotations

import json

import pytest

from physics_svg.presentation import parse_slide
from physics_svg.presentation.slides import load_all, load_template, slide_annotation
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
class TestTemplates:
    """The kind's starting points — one file each, and all of them valid.

    A template is not a new entity by the time this runs: the envelope is
    gone and what is left is a slide of this kind, which is exactly what
    makes the mechanism cheap (docs/slide-templates.md §2).
    """

    def test_the_kind_offers_at_least_one(self, kind) -> None:
        # A kind with no template is a kind the model has to invent from the
        # field table — the thing the library exists to prevent.
        assert kind.templates, f"у вида '{kind.tag}' нет заготовок в templates/"

    def test_every_template_is_a_valid_slide_of_this_kind(self, kind) -> None:
        # A whole slide, not a bare fragment: the slide is the smallest
        # thing that validates and the smallest thing the player shows.
        for template in kind.templates:
            slide = template.slide
            assert slide.get("type") == kind.tag, f"шаблон '{template.slug}' — не этот слайд"
            assert parse_slide(slide, template.slug) is not None

    def test_every_template_says_when_to_take_it(self, kind) -> None:
        # The catalogue is a table of these lines; an empty one makes the
        # row useless and the choice a guess.
        for template in kind.templates:
            assert template.when.strip(), f"шаблон '{template.slug}': пустое 'when'"

    def test_the_slug_matches_the_file_name(self, kind) -> None:
        for template in kind.templates:
            assert template.slug == template.path.stem


class TestTemplateEnvelope:
    def test_a_slug_that_disagrees_with_the_file_is_refused(self, tmp_path) -> None:
        path = tmp_path / "with-answer.json"
        path.write_text(
            json.dumps(
                {"template": "другое", "when": "…", "slide": {"type": "section", "text": "Итог"}},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="совпадать"):
            load_template(path)

    def test_a_broken_slide_inside_is_refused_with_a_path(self, tmp_path) -> None:
        # The envelope validates the slide with the ordinary union, so a
        # template breaks exactly like the slide it holds.
        path = tmp_path / "basic.json"
        path.write_text(
            json.dumps({"template": "basic", "when": "…", "slide": {"type": "section"}}),
            encoding="utf-8",
        )
        with pytest.raises(SchemaError, match="slide"):
            load_template(path)


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
