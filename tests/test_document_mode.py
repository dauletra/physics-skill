"""Режим «документ» (`--document`, document.build_plain_document):
произвольный текст + любое число визуалов, без вопросов и без режимов
student/teacher. Golden фиксирует полный конспект; отдельно — запрет
блоков листа (вопросы/part, с человеческой ошибкой и путём), уникальность
id, эскейпинг авторского текста, round-trip встроенного исходника и
сквозной прогон CLI."""
import json
import sys

import pytest

from test_escaping import ESCAPED, SENTINEL, STRUCTURAL_KEYS, poison
from test_source_embed import extract_source
from worksheet_builder.cli import main
from worksheet_builder.document import build_plain_document
from worksheet_builder.models import parse_document, parse_task

SAMPLE_DOC = {
    "title": "Конспект: равномерное движение",
    "blocks": [
        {"type": "heading", "text": "Основные понятия"},
        {"type": "text", "body": "Скорость υ показывает быстроту движения; путь s = υt."},
        {"type": "list", "items": ["Путь — скаляр.", "Скорость — вектор."], "marker": "number"},
        {"type": "heading", "text": "График и приборы"},
        {"type": "graph", "x_label": "t, с", "y_label": "s, м",
         "x_range": [0, 5], "y_range": [0, 50],
         "series": [{"label": "Тело", "points": [[0, 0], [5, 50]]}]},
        {"type": "row", "blocks": [
            {"type": "instrument", "kind": "speedometer", "unit": "км/ч",
             "min": 0, "max": 120, "step": 10, "value": 60, "caption": "Спидометр"},
            {"type": "text", "body": "Спидометр показывает модуль мгновенной скорости."},
        ]},
        {"type": "table", "headers": ["t, с", "s, м"], "rows": [["1", "10"], ["2", "20"]]},
    ],
}


def test_document_golden(golden):
    golden("document-notes", build_plain_document(parse_document(SAMPLE_DOC)))


def test_question_rejected_with_clear_error():
    with pytest.raises(ValueError, match="not allowed in a document"):
        parse_document({"blocks": [{"type": "open", "answer": "x"}]})


def test_question_inside_row_rejected_with_path():
    doc = {"blocks": [{"type": "row", "blocks": [
        {"type": "text", "body": "x"},
        {"type": "choice", "options": [{"text": "a", "correct": True}]},
    ]}]}
    with pytest.raises(ValueError, match=r"blocks\[0\].blocks\[1\]"):
        parse_document(doc)


def test_part_rejected():
    with pytest.raises(ValueError, match="'part'"):
        parse_document({"blocks": [{"type": "part", "blocks": [{"type": "open"}]}]})


def test_unknown_field_named():
    with pytest.raises(ValueError, match="subtitle"):
        parse_document({"title": "x", "subtitle": "y",
                        "blocks": [{"type": "text", "body": "b"}]})


def test_duplicate_ids_rejected():
    doc = {"blocks": [
        {"type": "text", "id": "b1", "body": "x"},
        {"type": "heading", "id": "b1", "text": "y"},
    ]}
    with pytest.raises(ValueError, match="duplicate block id"):
        parse_document(doc)


def test_heading_is_not_a_task_block():
    # Контр-проверка границы: словарь блоков листа не расширился.
    with pytest.raises(ValueError, match="'heading'"):
        parse_task({"id": "t", "blocks": [
            {"type": "heading", "text": "x"},
            {"type": "open"},
        ]})


def test_document_escapes_authored_text():
    # `label` в документе — свободный текст серии графика, а не буква part.
    spec = poison(SAMPLE_DOC, structural=STRUCTURAL_KEYS - {"label"})
    html = build_plain_document(parse_document(spec))
    assert SENTINEL not in html, "сырой HTML из данных просочился в рендер"
    assert ESCAPED in html, "сентинел вообще не попал в вывод"


def test_source_round_trips():
    html = build_plain_document(parse_document(SAMPLE_DOC),
                                source={"document": SAMPLE_DOC})
    assert extract_source(html) == {"document": SAMPLE_DOC}


def test_no_source_when_not_passed():
    assert "worksheet-source" not in build_plain_document(parse_document(SAMPLE_DOC))


def test_cli_document_end_to_end(tmp_path, monkeypatch):
    doc_path = tmp_path / "notes.json"
    doc_path.write_text(json.dumps(SAMPLE_DOC, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["render-worksheet", "--document", str(doc_path)])
    main()
    html = (tmp_path / "notes.html").read_text(encoding="utf-8")
    assert "Конспект: равномерное движение" in html
    # Исходник встроен всегда — у документа нет варианта без него.
    assert extract_source(html) == {"document": SAMPLE_DOC}
