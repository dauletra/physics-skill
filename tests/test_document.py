"""Смешанный документ (теория + задания вперемешку) — главное новое
качество единой архитектуры: golden полного документа, сквозная нумерация
task-блоков (теория номера не сдвигает), структурные запреты верхнего
уровня (вопрос/part вне task, task/row в верхнеуровневом row — с
человеческой ошибкой), валидация манифеста, эскейпинг и сквозной CLI."""
import sys

import pytest

from test_escaping import ESCAPED, SENTINEL, STRUCTURAL_KEYS, poison
from test_source_embed import extract_source, write_workspace
from worksheet_builder.cli import main
from worksheet_builder.document import build_document
from worksheet_builder.models import parse_block, parse_document

SAMPLE_SOURCE = {
    "document": {
        "title": "Равномерное движение: конспект и задачи",
        "header": {"subject": "Физика", "grade": "9",
                   "instructions": "Сначала прочитайте теорию, затем решите задачи."},
    },
    "blocks": [
        {"type": "heading", "id": "b1", "text": "Основные понятия"},
        {"type": "text", "id": "b2",
         "body": "Скорость υ показывает быстроту движения; путь s = υt."},
        {"type": "row", "id": "b3", "blocks": [
            {"type": "instrument", "kind": "speedometer", "unit": "км/ч",
             "min": 0, "max": 120, "step": 10, "value": 60, "caption": "Спидометр"},
            {"type": "text", "body": "Спидометр показывает модуль мгновенной скорости."},
        ]},
        {"type": "task", "id": "b4", "points": 2, "blocks": [
            {"type": "text", "body": "Найдите путь за t = 5 с при υ = 20 м/с."},
            {"type": "open", "answer": "s = 100 м"},
            {"type": "paper", "ruling": "lines", "rows": 2},
        ]},
        {"type": "heading", "id": "b5", "text": "График"},
        {"type": "graph", "id": "b6", "x_label": "t, с", "y_label": "s, м",
         "x_range": [0, 5], "y_range": [0, 50],
         "series": [{"label": "Тело", "points": [[0, 0], [5, 50]]}]},
        {"type": "task", "id": "b7", "blocks": [
            {"type": "text", "body": "Скорость — это скаляр или вектор?"},
            {"type": "choice", "options": [
                {"text": "скаляр"}, {"text": "вектор", "correct": True},
            ]},
        ]},
    ],
}


def parse_sample():
    doc = parse_document(SAMPLE_SOURCE["document"])
    blocks = [parse_block(raw) for raw in SAMPLE_SOURCE["blocks"]]
    return doc, blocks


def test_mixed_document_golden(golden):
    doc, blocks = parse_sample()
    golden("document-mixed", build_document(doc, blocks, with_answers=True))


def test_numbering_skips_theory_blocks():
    """Задания нумеруются сквозняком 1..N; заголовки/текст/графики между
    ними номера не сдвигают."""
    doc, blocks = parse_sample()
    html = build_document(doc, blocks, with_answers=True)
    assert '<span class="task-num">1.</span>' in html
    assert '<span class="task-num">2.</span>' in html
    assert '<span class="task-num">3.</span>' not in html


# --- Структурные запреты верхнего уровня ---

def test_top_level_question_rejected_with_clear_error():
    with pytest.raises(ValueError, match="inside a task"):
        parse_block({"id": "x", "type": "open", "answer": "y"})


def test_top_level_part_rejected():
    with pytest.raises(ValueError, match="inside a task"):
        parse_block({"id": "x", "type": "part", "blocks": [{"type": "open"}]})


def test_question_inside_top_row_rejected_with_path():
    with pytest.raises(ValueError, match=r"blocks\[1\]"):
        parse_block({"id": "x", "type": "row", "blocks": [
            {"type": "text", "body": "x"},
            {"type": "choice", "options": [{"text": "a", "correct": True}]},
        ]})


def test_task_inside_top_row_rejected():
    with pytest.raises(ValueError, match="cannot live inside a top-level row"):
        parse_block({"id": "x", "type": "row", "blocks": [
            {"type": "task", "blocks": [{"type": "open"}]},
        ]})


def test_nested_top_row_rejected():
    with pytest.raises(ValueError, match="cannot live inside a top-level row"):
        parse_block({"id": "x", "type": "row", "blocks": [
            {"type": "row", "blocks": [{"type": "text", "body": "x"}]},
        ]})


def test_heading_is_not_a_task_block():
    # Контр-проверка границы: внутри задания иерархию рисуют номер и буквы,
    # заголовков там нет.
    with pytest.raises(ValueError, match="'heading'"):
        parse_block({"type": "task", "id": "t", "blocks": [
            {"type": "heading", "text": "x"},
            {"type": "open"},
        ]})


# --- Манифест document.json ---

def test_manifest_unknown_field_named():
    with pytest.raises(ValueError, match="subtitle"):
        parse_document({"title": "x", "subtitle": "y"})


def test_manifest_header_unknown_field_named():
    with pytest.raises(ValueError, match="footer"):
        parse_document({"header": {"footer": "y"}})


def test_manifest_order_duplicates_named():
    with pytest.raises(ValueError, match="duplicates"):
        parse_document({"order": ["a", "b", "a"]})


# --- Эскейпинг и сквозной CLI ---

def test_document_escapes_authored_text():
    # `label` здесь — свободный текст серии графика, а не буква part.
    source = poison(SAMPLE_SOURCE, structural=STRUCTURAL_KEYS - {"label"})
    doc = parse_document(source["document"])
    blocks = [parse_block(raw) for raw in source["blocks"]]
    html = build_document(doc, blocks, with_answers=True)
    assert SENTINEL not in html, "сырой HTML из данных просочился в рендер"
    assert ESCAPED in html, "сентинел вообще не попал в вывод"


def test_cli_mixed_document_end_to_end(tmp_path, monkeypatch):
    write_workspace(tmp_path, SAMPLE_SOURCE)
    monkeypatch.setattr(sys, "argv", ["render-worksheet", str(tmp_path)])
    main()
    html = (tmp_path / "output" / "document.html").read_text(encoding="utf-8")
    assert "Равномерное движение: конспект и задачи" in html
    assert extract_source(html) == SAMPLE_SOURCE
    assert 'class="answers-section"' in html
