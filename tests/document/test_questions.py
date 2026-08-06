"""Properties every question kind must have, checked for all of them at once.

Written against the registry, so a new pedagogical kind is covered the moment
its module exists — including the escaping fuzz, which is the check most
easily forgotten by hand.
"""

from __future__ import annotations

from typing import Any, Iterator, Literal, Optional, get_args, get_origin

import pytest

from kinds import EACH_KIND
from physics_svg.document import build_document, parse_block, parse_document
from physics_svg.document.answers import Block, Inline, Rows
from physics_svg.document.blocks import doc_block_annotation
from physics_svg.document.questions import is_question, load_all, render_answer, render_body
from physics_svg.document.strings import LETTERS
from physics_svg.draw import esc
from physics_svg.schema import SchemaError, emit_schema, is_spec, spec_meta

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

    def test_has_a_reference_fragment_for_the_model(self, kind) -> None:
        assert kind.type.doc.exists(), f"нет {kind.type.doc}"
        assert kind.type.doc.read_text(encoding="utf-8").strip()

    def test_has_a_card_for_the_teacher(self, kind) -> None:
        # Two audiences, two texts: the card feeds the site, the fragment
        # feeds the bundle.
        assert kind.type.card.exists(), f"нет {kind.type.card}"
        text = kind.type.card.read_text(encoding="utf-8")
        assert text.strip().startswith("# ")
        assert "Что сказать Claude" in text, "в карточке нет примеров фраз для учителя"

    def test_has_a_human_title(self, kind) -> None:
        assert kind.type.title and kind.type.title != kind.tag

    def test_appears_in_the_published_schema(self, kind) -> None:
        schema = emit_schema({"block": doc_block_annotation()})
        assert kind.type.model.__name__ in schema["$defs"]

    def test_carries_the_standard_envelope(self, kind) -> None:
        # Numbering is container metadata and must not leak into a question;
        # id and explanation are the whole of the envelope.
        fields = spec_meta(kind.type.model).fields
        assert "id" in fields and "explanation" in fields
        assert "label" not in fields

    def test_has_a_place_in_the_reading_order(self, kind) -> None:
        # The site page and the reference index are ordered by this, so it is
        # the author's decision, not the alphabet of the latin tag.
        orders = [entry.order for entry in load_all().values()]
        assert orders == sorted(orders) and len(set(orders)) == len(orders)


@EACH_KIND
class TestDocumentedExample:
    def test_every_documented_example_is_a_valid_task(self, kind) -> None:
        # A whole task, not a bare payload: that is what the site prints and
        # what a teacher's draft will actually contain.
        for task in kind.tasks:
            assert task.get("type") == "task", f"пример '{kind.tag}' — не задание"
            assert parse_block(task, "t") is not None

    def test_the_example_carries_its_own_statement(self, kind) -> None:
        # The wording is part of the example, so nothing downstream has to
        # invent a statement for it — and a statement that stops matching the
        # answer is visible in one place.
        html = render_task(kind.task)
        assert '<div class="task"' in html
        assert esc(kind.statement) in html

    def test_the_answer_reaches_the_answers_section(self, kind) -> None:
        for task in kind.tasks:
            html = render_task(task)
            assert ANSWERS_MARKER in html, f"у вида '{kind.tag}' ответ не попал в секцию"

    def test_the_body_never_reveals_the_answer_section_markup(self, kind) -> None:
        for task in kind.tasks:
            body = build_document(EMPTY_DOC, [parse_block(task, "t")], with_answers=False)
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
                block = parse_block(kind.task_with(payload), "t")
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

    def test_every_string_of_the_payload_is_escaped(self, kind) -> None:
        """Author markup in every string of the payload at once, at any depth.

        The payload is **appended to** rather than substituted, and the same
        way everywhere, so a vocabulary and the answers that name it stay
        consistent: a word bank still contains its blanks, a `category` still
        names a group, `left[].match` still finds its `right[].id`. Otherwise
        the fuzz would break an invariant, the block would not parse, and the
        test would pass by rendering nothing.
        """
        patched = _fuzz(kind.example, _closed_fields(kind.type.model))
        html = build_document(EMPTY_DOC, [parse_block(kind.task_with(patched), "t")])
        assert "<script>alert" not in html, f"'{kind.tag}': авторский текст не экранирован"
        assert "&lt;script&gt;alert" in html


def _closed_fields(model: type, seen: Optional[set[type]] = None) -> set[str]:
    """Names of fields anywhere in a kind's models whose value is a `Literal`.

    Derived from the models, not listed by hand: appending anything to a closed
    vocabulary (`select`, `grid`, `style`) is not a fuzz, it is invalid data,
    and a new field of that shape must not quietly start skipping the check.
    """
    seen = seen if seen is not None else set()
    if model in seen:
        return set()
    seen.add(model)
    closed = set()
    for name, meta in spec_meta(model).fields.items():
        for annotation in _annotations(meta.annotation):
            if get_origin(annotation) is Literal:
                closed.add(name)
            elif is_spec(annotation):
                closed |= _closed_fields(annotation, seen)
    return closed


def _annotations(annotation: Any) -> Iterator[Any]:
    """The annotation itself and everything nested in it."""
    yield annotation
    for argument in get_args(annotation):
        if isinstance(argument, type) or get_origin(argument) is not None:
            yield from _annotations(argument)


def _fuzz(value: Any, closed: set[str]) -> Any:
    if isinstance(value, str):
        return value + PAYLOAD
    if isinstance(value, list):
        return [_fuzz(item, closed) for item in value]
    if isinstance(value, dict):
        # Keys are carriers of meaning, not author text: a `blanks` key has to
        # keep matching its `___name___` in the template.
        return {
            key: value[key] if key in closed else _fuzz(value[key], closed) for key in value
        }
    return value


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
        assert render_answer(OpenSpec(type="open", answer="15 м/с")) == Inline("15 м/с")

    def test_a_question_without_an_answer_says_so_with_none(self) -> None:
        from physics_svg.document.questions.open import OpenSpec

        # Not an empty `Inline`: the section skips the row, it does not print
        # a number with nothing after it.
        assert render_answer(OpenSpec(type="open")) is None

    def test_every_kind_has_both_renderers(self) -> None:
        for entry in load_all().values():
            assert callable(entry.body) and callable(entry.answer)


class TestPlotSharesTheGraphPlane:
    """`plot` renders by building a real `GraphSpec` out of the plane it
    inherits. A field of that plane it forgets to carry over would go silently
    dead on plotting questions while still working on illustrations."""

    def test_every_field_of_the_plane_reaches_the_graph(self) -> None:
        from physics_svg.document.questions.plot import PlotSpec
        from physics_svg.schema import parse
        from physics_svg.visuals.graph.model import GraphAxes

        question = parse(
            PlotSpec,
            {
                "type": "plot",
                "x_label": "t, с",
                "y_label": "s, м",
                "x_range": [0, 40],
                "y_range": [0, 30],
                "x_step": 5,
                "x_label_step": 10,
                "y_step": 5,
                "y_label_step": 10,
                "grid": "fine",
                "answer": [{"points": [[0, 0], [40, 30]]}],
            },
            name="plot",
        )
        graph = question.as_graph([])
        for name in spec_meta(GraphAxes).fields:
            assert getattr(graph, name) == getattr(question, name), name


@EACH_KIND
class TestAnswerShape:
    def test_the_answer_is_a_shape_and_not_markup(self, kind) -> None:
        """A kind describes its answer; the section lays it out."""
        assert _answer_of(kind) is None or isinstance(_answer_of(kind), (Inline, Rows, Block))

    def test_a_drawn_answer_is_a_block_and_a_short_one_is_not(self, kind) -> None:
        # The one thing the shapes exist to prevent: an SVG in the slot that
        # holds «б», or a picture folded into a semicolon-joined line.
        answer = _answer_of(kind)
        if isinstance(answer, Inline):
            assert "<svg" not in answer.html
        if isinstance(answer, Rows):
            assert all("<svg" not in row for row in answer.rows)


def _answer_of(kind) -> Any:
    task = parse_block(kind.task, "t")
    return render_answer(next(b for b in task.blocks if is_question(b)))


class TestLetteredStatements:
    """`true_false` prints а)/б)/в) beside its statements and names them by the
    same letters in the answers section — so it, too, ends where the alphabet
    does. Not a `Domain`: the student judges the statements, does not pick
    among them."""

    def test_statements_cannot_outgrow_the_alphabet(self) -> None:
        with pytest.raises(SchemaError, match="печатаются буквами"):
            parse_block(
                {
                    "type": "task",
                    "blocks": [
                        {"type": "text", "body": "Отметьте, верны ли утверждения."},
                        {
                            "type": "true_false",
                            "statements": [
                                {"text": f"Утверждение {i}", "answer": i % 2 == 0}
                                for i in range(len(LETTERS) + 1)
                            ],
                        },
                    ],
                },
                "t",
            )

    def test_the_answer_names_the_printed_letters(self) -> None:
        # The failure this guards: letters on the sheet, numbers in the answers.
        from physics_svg.document.questions.true_false import StatementSpec, TrueFalseSpec

        model = TrueFalseSpec(
            type="true_false",
            statements=[
                StatementSpec(text="Скорость — вектор", answer=True),
                StatementSpec(text="Путь бывает отрицательным", answer=False),
            ],
        )
        assert render_answer(model) == Inline("а — Верно, б — Неверно")
        assert '<span class="list-marker">а)</span>' in render_body(model)


class TestDomain:
    """The vocabulary a student chooses from, checked the same way everywhere."""

    def test_a_bank_without_the_right_word_is_rejected(self) -> None:
        # An unsolvable sheet that nothing on the page gives away.
        with pytest.raises(SchemaError, match="нет среди bank"):
            parse_block(
                {
                    "type": "task",
                    "blocks": [
                        {"type": "text", "body": "Вставьте слово."},
                        {
                            "type": "fill_text",
                            "template": "Скорость ___v___.",
                            "blanks": {"v": "постоянна"},
                            "bank": ["растёт", "равна нулю"],
                        },
                    ],
                },
                "t",
            )

    def test_a_duplicated_option_is_rejected(self) -> None:
        with pytest.raises(SchemaError, match="уникальны"):
            parse_block(
                {
                    "type": "task",
                    "blocks": [
                        {"type": "text", "body": "Выберите."},
                        {
                            "type": "choice",
                            "options": [
                                {"text": "Скорость постоянна", "correct": True},
                                {"text": "Скорость постоянна"},
                            ],
                        },
                    ],
                },
                "t",
            )

    def test_a_vocabulary_cannot_outgrow_the_alphabet(self) -> None:
        # `choice` prints letters through the same series as `match`, and used
        # to have no limit at all: option 28 raised IndexError while rendering.
        with pytest.raises(SchemaError, match="печатаются буквами"):
            parse_block(
                {
                    "type": "task",
                    "blocks": [
                        {"type": "text", "body": "Выберите."},
                        {
                            "type": "choice",
                            "select": "multiple",
                            "options": [
                                {"text": f"Вариант {i}", "correct": i == 0}
                                for i in range(len(LETTERS) + 1)
                            ],
                        },
                    ],
                },
                "t",
            )

    def test_the_group_of_an_item_must_exist(self) -> None:
        with pytest.raises(SchemaError, match=r"items\[1\].category"):
            parse_block(
                {
                    "type": "task",
                    "blocks": [
                        {"type": "text", "body": "Распределите."},
                        {
                            "type": "classify",
                            "categories": ["Механика"],
                            "items": [
                                {"text": "Падение", "category": "Механика"},
                                {"text": "Ток", "category": "Электричество"},
                            ],
                        },
                    ],
                },
                "t",
            )
