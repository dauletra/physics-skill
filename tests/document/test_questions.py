"""Properties every question kind must have, checked for all of them at once.

Written against the registry, so a new pedagogical kind is covered the moment
its module exists — including the escaping fuzz, which is the check most
easily forgotten by hand.
"""

from __future__ import annotations

import pytest
from kinds import EACH_KIND

from physics_svg.document import build_document, parse_block, parse_document
from physics_svg.document.blocks import doc_block_annotation
from physics_svg.document.questions import load_all, render_answer, render_body
from physics_svg.schema import SchemaError, emit_schema, spec_meta

PAYLOAD = '<script>alert("x")</script> & "кавычки"'
#: The page always carries KaTeX's <script> tags and the stylesheet mentions
#: every class name, so assertions match markup, not bare words.
ANSWERS_MARKER = '<div class="answers-section">'
EMPTY_DOC = parse_document({"title": "Проба"})


def render_task(data: dict) -> str:
    return build_document(EMPTY_DOC, [parse_block(data, "t")])


@EACH_KIND
class TestRegistry:
    def test_tag_matches_the_spec_literal(self, kind) -> None:
        assert spec_meta(kind.type.model).tag == kind.tag

    def test_has_a_reference_fragment(self, kind) -> None:
        assert kind.type.doc.exists(), f"нет {kind.type.doc}"
        assert kind.type.doc.read_text(encoding="utf-8").strip()

    def test_has_a_human_title(self, kind) -> None:
        assert kind.type.title and kind.type.title != kind.tag

    def test_appears_in_the_published_schema(self, kind) -> None:
        schema = emit_schema({"block": doc_block_annotation()})
        assert kind.type.model.__name__ in schema["$defs"]

    def test_carries_the_standard_envelope(self, kind) -> None:
        # Numbering and points are container metadata and must not leak into
        # a question; id and explanation are the whole of the envelope.
        fields = spec_meta(kind.type.model).fields
        assert "id" in fields and "explanation" in fields
        assert "label" not in fields and "points" not in fields


@EACH_KIND
class TestDocumentedExample:
    def test_the_example_in_the_reference_is_valid(self, kind) -> None:
        assert parse_block(kind.task(), "t") is not None

    def test_a_minimal_task_prints_something(self, kind) -> None:
        # A block that can render to nothing is either not a block, or its
        # schema must require a neighbour that prints for it (`open` does).
        html = render_task(kind.task())
        assert '<div class="task"' in html
        assert "Условие задания." in html

    def test_the_answer_reaches_the_answers_section(self, kind) -> None:
        html = render_task(kind.task())
        assert ANSWERS_MARKER in html, f"у вида '{kind.tag}' ответ не попал в секцию"

    def test_the_body_never_reveals_the_answer_section_markup(self, kind) -> None:
        body = build_document(EMPTY_DOC, [parse_block(kind.task(), "t")], with_answers=False)
        assert ANSWERS_MARKER not in body


@EACH_KIND
class TestEscaping:
    def test_free_text_fields_are_escaped(self, kind) -> None:
        """Author markup in any string field, one field at a time."""
        injected = 0
        for key, value in kind.example.items():
            if not isinstance(value, str) or key == "type":
                continue
            payload = {**kind.example, key: PAYLOAD}
            try:
                block = parse_block(
                    {"type": "task", "blocks": [{"type": "text", "body": "Условие."}, payload]},
                    "t",
                )
            except SchemaError:
                continue  # a closed vocabulary, not free text
            html = build_document(EMPTY_DOC, [block])
            # The page carries KaTeX's own <script> tags, so the assertion is
            # on the injected payload rather than on the tag name.
            assert "<script>alert" not in html, f"'{kind.tag}': поле '{key}' не экранировано"
            assert "&lt;script&gt;alert" in html
            injected += 1
        if injected == 0:
            pytest.skip("в примере нет свободного текста верхнего уровня")

    def test_nested_text_is_escaped_too(self, kind) -> None:
        """The payload of most kinds is a list of objects, and their text is
        exactly where escaping is easiest to miss."""
        example = kind.example
        patched = {
            key: _inject(value) if isinstance(value, list) else value
            for key, value in example.items()
        }
        try:
            block = parse_block(
                {"type": "task", "blocks": [{"type": "text", "body": "Условие."}, patched]}, "t"
            )
        except SchemaError:
            pytest.skip("подставленный текст ломает инварианты вида")
        assert "<script>alert" not in build_document(EMPTY_DOC, [block])


def _inject(items: list) -> list:
    patched = []
    for item in items:
        if isinstance(item, dict) and "text" in item:
            patched.append({**item, "text": PAYLOAD})
        elif isinstance(item, str):
            patched.append(PAYLOAD)
        else:
            patched.append(item)
    return patched


class TestAnswers:
    def test_open_without_an_answer_gets_no_row(self) -> None:
        html = render_task(
            {
                "type": "task",
                "blocks": [{"type": "text", "body": "Обсудите устно."}, {"type": "open"}],
            }
        )
        # An empty answers section is not printed at all — a lesson summary
        # simply has none.
        assert ANSWERS_MARKER not in html

    def test_open_body_is_empty_but_the_task_still_prints(self) -> None:
        from physics_svg.document.questions.open import OpenSpec

        assert render_body(OpenSpec(type="open")) == ""
        assert render_answer(OpenSpec(type="open", answer="15 м/с")) == "15 м/с"

    def test_every_kind_has_both_renderers(self) -> None:
        for entry in load_all().values():
            assert callable(entry.body) and callable(entry.answer)
