"""Assembling a whole document: numbering, answers, the embedded draft, the
workspace loader, and a golden of the worked example.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest

from physics_svg.document import (
    WorkspaceError,
    build_document,
    build_preview,
    load_workspace,
    parse_block,
    parse_document,
)

REPO = Path(__file__).resolve().parent.parent.parent
EXAMPLE = REPO / "examples" / "kinematics-9th-grade"
GOLDEN = REPO / "tests" / "golden" / "document"
REGENERATE = os.environ.get("REGEN_GOLDEN") == "1"

#: The stylesheet mentions every class name, so assertions match markup.
ANSWERS_MARKER = '<div class="answers-section">'

TEXT = {"type": "text", "body": "Условие."}
OPEN = {"type": "open", "answer": "42"}


def task(*blocks: dict, **extra: object) -> dict:
    return {"type": "task", "blocks": list(blocks), **extra}


def document(*raw_blocks: dict, **manifest: object) -> str:
    doc = parse_document(manifest or {"title": "Документ"})
    blocks = [parse_block(raw, f"b{i}") for i, raw in enumerate(raw_blocks)]
    return build_document(doc, blocks)


class TestNumbering:
    def test_tasks_are_numbered_in_order(self) -> None:
        html = document(task(TEXT, OPEN), task(TEXT, OPEN))
        assert re.findall(r'class="task-num">(\d+)\.', html) == ["1", "2"]

    def test_theory_between_tasks_does_not_shift_the_numbering(self) -> None:
        html = document(
            task(TEXT, OPEN),
            {"type": "heading", "text": "Раздел"},
            TEXT,
            task(TEXT, OPEN),
        )
        assert re.findall(r'class="task-num">(\d+)\.', html) == ["1", "2"]

    def test_answers_use_the_same_numbers(self) -> None:
        html = document(TEXT, task(TEXT, OPEN))
        section = html.split(ANSWERS_MARKER)[1]
        assert ">1.<" in section

    def test_a_subtask_answer_carries_its_letter(self) -> None:
        html = document(
            task(TEXT, {"type": "part", "blocks": [OPEN]}, {"type": "part", "blocks": [OPEN]})
        )
        section = html.split(ANSWERS_MARKER)[1]
        assert "1. а)" in section and "1. б)" in section


class TestAnswersSection:
    def test_a_document_without_questions_has_no_section(self) -> None:
        html = document({"type": "heading", "text": "Конспект"}, TEXT)
        assert ANSWERS_MARKER not in html

    def test_the_handout_has_no_section(self) -> None:
        doc = parse_document({"title": "Т"})
        blocks = [parse_block(task(TEXT, OPEN), "t")]
        assert ANSWERS_MARKER not in build_document(doc, blocks, with_answers=False)
        assert ANSWERS_MARKER in build_document(doc, blocks)

    def test_bodies_are_identical_with_and_without_answers(self) -> None:
        # The handout is the same document minus a section, not a second
        # rendering of the bodies — that is what makes a leak impossible.
        doc = parse_document({"title": "Т"})
        blocks = [parse_block(task(TEXT, OPEN), "t")]
        full = build_document(doc, blocks).split(ANSWERS_MARKER)[0]
        handout = build_document(doc, blocks, with_answers=False)
        assert full.rstrip() in handout or handout.startswith(full[:200])

    def test_an_explanation_is_printed_with_the_answer(self) -> None:
        html = document(task(TEXT, {**OPEN, "explanation": "по формуле пути"}))
        assert "Пояснение:" in html and "по формуле пути" in html


class TestEmbeddedDraft:
    def test_the_draft_round_trips(self) -> None:
        raw_doc = {"title": "Документ", "order": ["t1"]}
        raw_blocks = [{**task(TEXT, OPEN), "id": "t1"}]
        doc = parse_document(raw_doc)
        blocks = [parse_block(raw_blocks[0], "t1")]
        html = build_document(doc, blocks, source={"document": raw_doc, "blocks": raw_blocks})
        payload = re.search(
            r'<script type="application/json" id="document-source">(.*?)</script>', html, re.S
        )
        assert payload is not None
        assert json.loads(payload.group(1)) == {"document": raw_doc, "blocks": raw_blocks}

    def test_author_text_cannot_close_the_script_tag(self) -> None:
        raw_blocks = [{"type": "text", "body": "</script><script>alert(1)</script>", "id": "b"}]
        doc = parse_document({"order": ["b"]})
        html = build_document(
            doc,
            [parse_block(raw_blocks[0], "b")],
            source={"document": {}, "blocks": raw_blocks},
        )
        script = html.split('id="document-source">')[1]
        assert "</script><script>" not in script.split("</script>")[0]

    def test_a_handout_carries_no_draft(self) -> None:
        # It would reveal the answers through the page source.
        doc = parse_document({})
        blocks = [parse_block(task(TEXT, OPEN), "t")]
        assert "document-source" not in build_document(doc, blocks, with_answers=False)

    def test_a_preview_carries_no_draft(self) -> None:
        doc = parse_document({"order": ["t1"]})
        blocks = [parse_block({**task(TEXT, OPEN), "id": "t1"}, "t1")]
        assert "document-source" not in build_preview(doc, blocks, "t1")


class TestPreview:
    def test_a_block_keeps_its_real_number_and_answers(self) -> None:
        doc = parse_document({"order": ["a", "b"]})
        blocks = [
            parse_block({**task(TEXT, OPEN), "id": "a"}, "a"),
            parse_block({**task(TEXT, OPEN), "id": "b"}, "b"),
        ]
        html = build_preview(doc, blocks, "b")
        assert 'class="task-num">2.' in html
        assert ANSWERS_MARKER in html

    def test_an_unknown_block_id(self) -> None:
        doc = parse_document({})
        with pytest.raises(KeyError):
            build_preview(doc, [], "missing")


class TestWorkspace:
    def test_the_worked_example_loads(self) -> None:
        workspace = load_workspace(EXAMPLE)
        assert len(workspace.blocks) == len(workspace.raw_blocks) >= 15

    def test_a_missing_manifest(self, tmp_path: Path) -> None:
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert "document.json" in str(info.value)

    def test_a_block_file_not_listed_in_order(self, tmp_path: Path) -> None:
        _draft(tmp_path, {"order": ["a"]}, {"a": {**task(TEXT, OPEN), "id": "a"},
                                            "b": {**task(TEXT, OPEN), "id": "b"}})
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert "не перечислены" in str(info.value)

    def test_an_id_that_disagrees_with_the_file_name(self, tmp_path: Path) -> None:
        _draft(tmp_path, {"order": ["a"]}, {"a": {**task(TEXT, OPEN), "id": "wrong"}})
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert "не совпадает с именем файла" in str(info.value)

    def test_a_missing_block_file(self, tmp_path: Path) -> None:
        _draft(tmp_path, {"order": ["a", "ghost"]}, {"a": {**task(TEXT, OPEN), "id": "a"}})
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert "не найден файл блока" in str(info.value)

    def test_broken_json(self, tmp_path: Path) -> None:
        _draft(tmp_path, {"order": ["a"]}, {})
        (tmp_path / "blocks" / "a.json").write_text("{нет", encoding="utf-8")
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert "невалидный JSON" in str(info.value)

    def test_every_problem_is_reported_at_once(self, tmp_path: Path) -> None:
        _draft(
            tmp_path,
            {"order": ["a", "b"]},
            {"a": {"type": "task", "id": "a", "blocks": [OPEN]},
             "b": {"type": "task", "id": "wrong", "blocks": [OPEN]}},
        )
        with pytest.raises(WorkspaceError) as info:
            load_workspace(tmp_path)
        assert len(info.value.problems) >= 3

    def test_without_order_the_files_are_taken_as_they_sort(self, tmp_path: Path) -> None:
        _draft(tmp_path, {}, {"a": {**task(TEXT, OPEN), "id": "a"},
                              "b": {**task(TEXT, OPEN), "id": "b"}})
        assert len(load_workspace(tmp_path).blocks) == 2


def _draft(root: Path, manifest: dict, blocks: dict) -> None:
    (root / "blocks").mkdir(parents=True, exist_ok=True)
    (root / "document.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for name, block in blocks.items():
        (root / "blocks" / f"{name}.json").write_text(
            json.dumps(block, ensure_ascii=False), encoding="utf-8"
        )


class TestRowColumns:
    def test_the_column_count_reaches_the_markup(self) -> None:
        html = document(
            task(
                TEXT,
                {
                    "type": "row",
                    "columns": 2,
                    "blocks": [{"type": "part", "blocks": [OPEN]} for _ in range(4)],
                },
            )
        )
        assert html.count('class="task-row cols-2"') == 1
        assert html.count('class="task-col"') == 4

    def test_a_row_without_a_count_renders_as_before(self) -> None:
        html = document(task(TEXT, {"type": "row", "blocks": [TEXT, TEXT]}))
        assert 'class="task-row"' in html

    def test_the_fold_is_counted_not_balanced(self) -> None:
        """Columns fill downwards, so which item ends the left column is a
        promise: it is the row count that says so, not the items' height."""
        html = document(
            task(
                TEXT,
                {
                    "type": "row",
                    "columns": 2,
                    "blocks": [{"type": "part", "blocks": [OPEN]} for _ in range(7)],
                },
            )
        )
        assert 'style="grid-template-rows: repeat(4, auto);"' in html
        assert re.findall(r'class="subtask-label">(\w)\)', html) == list("абвгдеж")


class TestGolden:
    def test_the_worked_example_matches_its_golden(self) -> None:
        workspace = load_workspace(EXAMPLE)
        actual = build_document(workspace.document, workspace.blocks, source=workspace.source)
        _compare(GOLDEN / "example.html", actual)

    def test_a_mixed_document_matches_its_golden(self) -> None:
        """Theory and tasks interleaved — the most common genre, and the one
        where numbering and the answers section can disagree."""
        actual = document(
            {"type": "heading", "text": "Теория"},
            TEXT,
            task(TEXT, OPEN, {"type": "answer_line"}),
            {"type": "row", "blocks": [TEXT, {"type": "list", "items": ["раз", "два"]}]},
            task(
                TEXT,
                {"type": "part", "blocks": [{"type": "text", "body": "а"}, OPEN]},
                {"type": "part", "blocks": [{"type": "text", "body": "б"},
                                            {"type": "paper", "ruling": "lines", "rows": 2},
                                            OPEN]},
            ),
            title="Смешанный документ",
        )
        _compare(GOLDEN / "mixed.html", actual)


def _compare(path: Path, actual: str) -> None:
    if REGENERATE or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        if not REGENERATE:
            return
    assert actual == path.read_text(encoding="utf-8"), (
        f"рендер разошёлся с эталоном {path.name}; если изменение намеренное — "
        "REGEN_GOLDEN=1 и просмотри диф глазами"
    )
