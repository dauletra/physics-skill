"""Composition rules of the block tree.

The point of these invariants is that ambiguous documents are *inexpressible*
rather than "allowed but interpreted cleverly". The numbering rule stays one
line — a letter is a `part`, in order — precisely because the shapes that
would complicate it are rejected here.
"""

from __future__ import annotations

import pytest

from physics_svg.document import parse_block, part_labels
from physics_svg.document.containers import PartSpec
from physics_svg.schema import SchemaError

TEXT = {"type": "text", "body": "Условие."}
OPEN = {"type": "open", "answer": "42"}
CHOICE = {"type": "choice", "options": [{"text": "а", "correct": True}, {"text": "б"}]}


def task(*blocks: dict, **extra: object) -> dict:
    return {"type": "task", "blocks": list(blocks), **extra}


def rejects(data: dict, fragment: str) -> None:
    with pytest.raises(SchemaError) as info:
        parse_block(data, "t")
    assert fragment in str(info.value), f"ожидался фрагмент {fragment!r}, получено:\n{info.value}"


class TestCondition:
    def test_a_question_needs_a_statement(self) -> None:
        rejects(task(OPEN), "нет условия")

    def test_a_task_level_statement_covers_every_part(self) -> None:
        block = task(
            TEXT,
            {"type": "part", "blocks": [OPEN]},
            {"type": "part", "blocks": [CHOICE]},
        )
        assert parse_block(block, "t") is not None

    def test_a_part_without_any_statement_on_its_path(self) -> None:
        rejects(
            task({"type": "part", "blocks": [TEXT, OPEN]}, {"type": "part", "blocks": [CHOICE]}),
            "у подзадания нет условия",
        )

    def test_only_text_counts_as_a_statement(self) -> None:
        # A graph caption or list items are not promoted to the role.
        rejects(task({"type": "list", "items": ["раз"]}, OPEN), "нет условия")

    def test_the_error_names_the_offending_block(self) -> None:
        with pytest.raises(SchemaError) as info:
            parse_block(task({"type": "list", "items": ["раз"]}, OPEN), "task-07")
        assert "blocks[1]" in str(info.value)


class TestComposition:
    def test_a_part_and_a_bare_question_cannot_be_siblings(self) -> None:
        rejects(task(TEXT, {"type": "part", "blocks": [CHOICE]}, OPEN), "не бывают соседями")

    def test_two_bare_questions(self) -> None:
        rejects(task(TEXT, OPEN, CHOICE), "больше одного вопроса")

    def test_a_part_needs_exactly_one_question(self) -> None:
        rejects(task(TEXT, {"type": "part", "blocks": [TEXT]}), "ровно один вопрос")
        rejects(task(TEXT, {"type": "part", "blocks": [OPEN, CHOICE]}), "ровно один вопрос")

    def test_parts_do_not_nest(self) -> None:
        rejects(
            task(TEXT, {"type": "part", "blocks": [{"type": "part", "blocks": [OPEN]}]}),
            "нельзя вложить",
        )

    def test_rows_do_not_nest(self) -> None:
        rejects(
            task(TEXT, {"type": "row", "blocks": [{"type": "row", "blocks": [TEXT]}]}),
            "нельзя вложить в строку",
        )

    def test_ids_are_unique_within_a_task(self) -> None:
        rejects(
            task({**TEXT, "id": "x"}, {**OPEN, "id": "x"}),
            "повторяется",
        )


class TestRowIsTransparent:
    def test_a_part_inside_a_row_still_counts_as_a_part(self) -> None:
        # Two parts wrapped in a row must be rejected next to a bare question
        # exactly as they would be standing at task level.
        rejects(
            task(
                TEXT,
                {"type": "row", "blocks": [{"type": "part", "blocks": [CHOICE]}]},
                OPEN,
            ),
            "не бывают соседями",
        )

    def test_a_row_of_parts_is_lettered_as_if_flat(self) -> None:
        block = parse_block(
            task(
                TEXT,
                {
                    "type": "row",
                    "blocks": [
                        {"type": "part", "blocks": [OPEN]},
                        {"type": "part", "blocks": [CHOICE]},
                    ],
                },
            ),
            "t",
        )
        from physics_svg.document import task_part_labels

        assert sorted(task_part_labels(block).values()) == ["а", "б"]


class TestLettering:
    def test_letters_follow_the_order_of_parts(self) -> None:
        parts = [PartSpec(type="part", blocks=[OPEN]) for _ in range(3)]
        assert list(part_labels(parts).values()) == ["а", "б", "в"]

    def test_an_explicit_letter_wins_and_is_skipped_by_the_automatic_ones(self) -> None:
        parts = [
            PartSpec(type="part", blocks=[OPEN]),
            PartSpec(type="part", blocks=[OPEN], label="а"),
            PartSpec(type="part", blocks=[OPEN]),
        ]
        assert list(part_labels(parts).values()) == ["б", "а", "в"]

    def test_lettering_is_pure(self) -> None:
        parts = [PartSpec(type="part", blocks=[OPEN]) for _ in range(2)]
        assert part_labels(parts) == part_labels(parts)

    def test_an_explicit_letter_must_be_from_the_series(self) -> None:
        rejects(task(TEXT, {"type": "part", "blocks": [OPEN], "label": "z"}), "должна быть одной из")

    def test_duplicate_explicit_letters(self) -> None:
        rejects(
            task(
                TEXT,
                {"type": "part", "blocks": [OPEN], "label": "а"},
                {"type": "part", "blocks": [CHOICE], "label": "а"},
            ),
            "повторяются",
        )


class TestTopLevel:
    def test_a_question_cannot_live_outside_a_task(self) -> None:
        rejects(OPEN, "неизвестный тип блока")

    def test_a_part_cannot_live_outside_a_task(self) -> None:
        rejects({"type": "part", "blocks": [OPEN]}, "неизвестный тип блока")

    def test_a_top_level_row_takes_components_only(self) -> None:
        assert parse_block(
            {"type": "row", "blocks": [TEXT, {"type": "list", "items": ["раз"]}]}, "r"
        ) is not None
        rejects({"type": "row", "blocks": [task(TEXT, OPEN)]}, "неизвестный тип блока")

    def test_components_and_headings_are_top_level_blocks(self) -> None:
        for block in (TEXT, {"type": "heading", "text": "Раздел"},
                      {"type": "paper", "ruling": "lines", "rows": 3}):
            assert parse_block(block, "b") is not None
