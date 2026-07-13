"""Общие фикстуры: golden-сравнение и минимальные задания на каждый вид.

Пересъём эталонов: REGEN_GOLDEN=1 python -m pytest tests
(пересобирает файлы в tests/golden/ вместо сравнения — использовать только
когда изменение рендера намеренное, и просматривать диф глазами)."""
import os
from pathlib import Path

import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"


@pytest.fixture
def golden():
    def check(name, actual: str):
        path = GOLDEN_DIR / f"{name}.html"
        if os.environ.get("REGEN_GOLDEN"):
            GOLDEN_DIR.mkdir(exist_ok=True)
            path.write_text(actual, encoding="utf-8")
            return
        assert path.exists(), (
            f"Нет эталона {path.name} — пересними: REGEN_GOLDEN=1 pytest"
        )
        expected = path.read_text(encoding="utf-8")
        assert actual == expected, f"Рендер разошёлся с эталоном {path.name}"

    return check


# Минимальное валидное задание на каждый вид вопроса — самодостаточные
# фикстуры-словари, форма — по references/task-schema.md.
MINIMAL_TASKS = {
    "open": {
        "id": "t-open",
        "points": 2,
        "blocks": [
            {"type": "text", "body": "Путь при υ = 20 м/с за t = 5 с?"},
            {"type": "open", "response": "lines:2", "answer": "s = υt = 100 м",
             "explanation": "Равномерное движение."},
        ],
    },
    "choice": {
        "id": "t-choice",
        "blocks": [
            {"type": "text", "body": "Скорость — это..."},
            {"type": "choice", "select": "single", "options": [
                {"text": "скаляр"},
                {"text": "вектор", "correct": True},
                {"text": "число & знак"},
            ]},
        ],
    },
    "match": {
        "id": "t-match",
        "blocks": [
            {"type": "match",
             "left": [
                 {"text": "Скорость", "match": "ms"},
                 {"text": "Путь", "match": "m"},
             ],
             "right": [
                 {"id": "m", "text": "м"},
                 {"id": "ms", "text": "м/с"},
                 {"id": "n", "text": "Н"},
             ]},
        ],
    },
    "fill_text": {
        "id": "t-fill-text",
        "blocks": [
            {"type": "fill_text",
             "template": "Сила измеряется в ___u___.",
             "blanks": {"u": "ньютонах"},
             "bank": ["ньютонах", "джоулях"]},
        ],
    },
    "fill_table": {
        "id": "t-fill-table",
        "blocks": [
            {"type": "fill_table",
             "headers": ["t, с", "s, м"],
             "rows": [["0", "0"], ["1", {"answer": "5"}]]},
        ],
    },
    "plot": {
        "id": "t-plot",
        "blocks": [
            {"type": "plot", "x_label": "t, с", "y_label": "υ, м/с",
             "x_range": [0, 5], "y_range": [0, 10],
             "given": [{"points": [[0, 0]], "style": "solid"}],
             "answer": [{"points": [[0, 0], [4, 8]], "style": "solid"}]},
        ],
    },
    "true_false": {
        "id": "t-tf",
        "blocks": [
            {"type": "true_false", "statements": [
                {"text": "Скорость — вектор.", "answer": True},
                {"text": "Путь — вектор.", "answer": False},
            ]},
        ],
    },
    "rank": {
        "id": "t-rank",
        "blocks": [
            {"type": "rank", "items": [
                {"text": "Поезд: 120 км/ч", "position": 3},
                {"text": "Пешеход: 5 км/ч", "position": 1},
                {"text": "Автомобиль: 60 км/ч", "position": 2},
            ]},
        ],
    },
    "classify": {
        "id": "t-classify",
        "blocks": [
            {"type": "classify",
             "categories": ["Твёрдое", "Жидкое", "Газообразное"],
             "items": [
                 {"text": "Железо", "category": "Твёрдое"},
                 {"text": "Вода", "category": "Жидкое"},
             ]},
        ],
    },
    # Составное задание: общий контекст + два part (буквы/баллы на part).
    "composite": {
        "id": "t-composite",
        "points": 5,
        "blocks": [
            {"type": "text", "body": "Общее условие с графиком."},
            {"type": "graph", "x_label": "t, с", "y_label": "υ, м/с",
             "x_range": [0, 5], "y_range": [0, 10],
             "series": [{"label": "Тело", "points": [[0, 0], [4, 8]], "style": "solid"}]},
            {"type": "part", "points": 2, "blocks": [
                {"type": "text", "body": "Найдите ускорение."},
                {"type": "open", "response": "lines:2", "answer": "a = 2 м/с²"},
            ]},
            {"type": "part", "points": 3, "blocks": [
                {"type": "text", "body": "Найдите путь."},
                {"type": "open", "response": "blank", "answer": "s = 16 м"},
            ]},
        ],
    },
    # row из двух part + чистые компоненты table и list.
    "row_and_components": {
        "id": "t-row",
        "blocks": [
            {"type": "table", "headers": ["x", "y"], "rows": [["1", "2"]]},
            {"type": "list", "items": ["Один", "Два"], "marker": "letter", "columns": "single"},
            {"type": "row", "blocks": [
                {"type": "part", "blocks": [
                    {"type": "text", "body": "Левая колонка."},
                    {"type": "open", "response": "none"},
                ]},
                {"type": "part", "blocks": [
                    {"type": "text", "body": "Правая колонка."},
                    {"type": "open", "response": "none"},
                ]},
            ]},
        ],
    },
}
