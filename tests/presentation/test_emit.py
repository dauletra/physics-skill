"""Emitting a presentation: the canonical JSON, the page, and the promises
that hold them together.

Three invariants from docs/presentation.md §9: the canon is deterministic
and golden; the blob is extractable from the built page byte-for-value; and
author text cannot break out of the data block — the fuzz goes through the
JSON gate the way the document's fuzz goes through the HTML and XML gates.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from physics_svg.presentation import (
    FORMAT,
    build_data,
    build_page,
    data_json,
    extract_data,
    load_workspace,
    parse_slide,
)
from physics_svg.presentation.slides import load_all
from physics_svg.schema import SchemaError

REPO = Path(__file__).resolve().parent.parent.parent
LESSON = Path(__file__).parent / "lesson"
GOLDEN = REPO / "tests" / "golden" / "presentation" / "lesson.json"
REGENERATE = os.environ.get("REGEN_GOLDEN") == "1"

PAYLOAD = '</script><script>alert("x")</script> & "кавычки"'

KINDS = list(load_all().values())
EACH_KIND = pytest.mark.parametrize("kind", KINDS, ids=[k.tag for k in KINDS])


def lesson_data() -> dict:
    workspace = load_workspace(LESSON)
    return build_data(workspace.presentation, workspace.slides)


def of_type(data: dict, tag: str) -> list[dict]:
    """Slides of one kind — the fixture is a lesson, not a fixed layout, and
    a test that says «the third slide» breaks the moment the lesson grows."""
    return [slide for slide in data["slides"] if slide["type"] == tag]


class TestCanonical:
    def test_the_envelope_names_its_contract(self) -> None:
        data = lesson_data()
        assert data["format"] == FORMAT
        assert data["title"] == "Равноускоренное движение"
        # The fixture is a whole lesson, and it carries every kind there is:
        # a type the lesson never uses is a type nothing ever emitted.
        assert [slide["type"] for slide in data["slides"]] == [
            "title",
            "objectives",
            "section",
            "content",
            "formula",
            "compare",
            "example",
            "section",
            "board_task",
            "tasks",
            "prompt",
            "reflection",
        ]
        assert {slide["type"] for slide in data["slides"]} == set(load_all())

    def test_two_builds_are_identical(self) -> None:
        # Determinism is what the golden stands on — same rule as the .docx.
        assert data_json(lesson_data()) == data_json(lesson_data())

    def test_the_golden_lesson(self) -> None:
        built = data_json(lesson_data())
        if REGENERATE:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(built, encoding="utf-8")
        assert GOLDEN.exists(), "нет эталона: REGEN_GOLDEN=1 и просмотри диф глазами"
        assert built == GOLDEN.read_text(encoding="utf-8"), (
            "канонический JSON разошёлся с эталоном; изменение намеренное — "
            "REGEN_GOLDEN=1 и просмотри диф глазами"
        )


class TestVisuals:
    def test_a_visual_carries_spec_svg_and_frame(self) -> None:
        visual = of_type(lesson_data(), "content")[0]["visual"]
        assert visual["spec"]["type"] == "graph"
        assert visual["svg"].startswith("<svg")
        assert visual["width"] > 0 and visual["height"] > 0

    def test_the_spec_survives_as_a_valid_author_spec(self) -> None:
        # What the wire carries must re-validate: that is what lets a server
        # re-render or edit the picture later.
        from physics_svg.visuals import parse_visual

        visual = of_type(lesson_data(), "board_task")[0]["visual"]
        assert parse_visual(visual["spec"], "wire") is not None

    def test_two_pictures_get_their_own_id_scope(self) -> None:
        # Ids are global inside a page, and every slide lives in one page:
        # the same picture twice must not make two elements share an id.
        from physics_svg.presentation.emit import emit_visual
        from physics_svg.visuals import parse_visual

        spec = json.loads(
            (REPO / "src/physics_svg/visuals/paper/specs/grid.json").read_text(encoding="utf-8")
        )
        model = parse_visual(spec, "wire")
        first = set(re.findall(r'id="([^"]+)"', emit_visual(model, "s1")["svg"]))
        second = set(re.findall(r'id="([^"]+)"', emit_visual(model, "s2")["svg"]))
        assert first, "у разлиновки нет ни одного id — проверять нечего, возьми другой тип"
        assert not (first & second), f"слайды делят id: {sorted(first & second)}"

    def test_two_pictures_on_one_slide_get_their_own_id_scope(self) -> None:
        # A slide used to hold at most one picture, so the slide's own scope
        # was enough. `compare` and `tasks` broke that: a kind that emits
        # several visuals owes each of them a scope of its own.
        cases = of_type(lesson_data(), "compare")[0]["cases"]
        drawn = [case["visual"]["svg"] for case in cases if "visual" in case]
        assert len(drawn) > 1, "в фикстуре нет слайда с двумя картинками — проверять нечего"
        ids = [set(re.findall(r'id="([^"]+)"', svg)) for svg in drawn]
        assert not (ids[0] & ids[1]), f"картинки одного слайда делят id: {sorted(ids[0] & ids[1])}"


class TestPage:
    def test_the_blob_comes_back_out(self) -> None:
        # Extractability is an invariant, not a promise: the future server
        # migration reads files already in teachers' hands.
        data = lesson_data()
        assert extract_data(build_page(data)) == data

    def test_author_text_cannot_close_the_data_block(self) -> None:
        model = parse_slide({"type": "title", "text": PAYLOAD}, "s")
        workspace = load_workspace(LESSON)
        data = build_data(workspace.presentation, [model])
        page = build_page(data)
        assert "</script><script>alert" not in page, "авторский текст закрыл блок данных"
        assert extract_data(page) == data, "экранирование исказило данные"

    def test_the_page_is_a_whole_document(self) -> None:
        page = build_page(lesson_data())
        assert page.lstrip().lower().startswith("<!doctype html>")
        assert "__PRESENTATION_DATA__" not in page


@EACH_KIND
class TestEmittedKinds:
    def test_every_documented_example_emits(self, kind) -> None:
        for example in kind.examples:
            emitted = kind.emit(parse_slide(example, "s"), "s1")
            assert emitted["type"] == kind.tag
            json.dumps(emitted, ensure_ascii=False)  # wire-serialisable

    def test_author_text_survives_the_json_gate(self, kind) -> None:
        """The payload fuzz, field by field — the mirror of the document's.

        Every template, not just the first: a field that only one of them
        fills (`answer` in a task, `visual` in an explanation) is still a
        field author text reaches the page through.
        """
        for example in kind.examples:
            for key, value in example.items():
                if not isinstance(value, str) or key in ("type", "id"):
                    continue
                try:
                    model = parse_slide({**example, key: PAYLOAD}, "s")
                except SchemaError:
                    continue  # a closed vocabulary, not free text
                page = build_page(
                    {"format": FORMAT, "title": "", "slides": [kind.emit(model, "s1")]}
                )
                assert "</script><script>alert" not in page, f"'{kind.tag}': поле '{key}'"
                extracted = extract_data(page)
                texts = json.dumps(extracted, ensure_ascii=False)
                assert "alert" in texts, f"'{kind.tag}': поле '{key}' потерялось по дороге"
