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
    def check(name, actual: str, ext: str = "html"):
        path = GOLDEN_DIR / f"{name}.{ext}"
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


# Минимальный валидный блок-задание на каждый вид вопроса — самодостаточные
# фикстуры-словари, форма — по references/document-schema.md (верхнеуровневый
# блок с type: "task").
MINIMAL_TASKS = {
    "open": {
        "type": "task",
        "id": "t-open",
        "points": 2,
        "blocks": [
            {"type": "text", "body": "Путь при υ = 20 м/с за t = 5 с?"},
            {"type": "open", "response": "lines:2", "answer": "s = υt = 100 м",
             "explanation": "Равномерное движение."},
        ],
    },
    "choice": {
        "type": "task",
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
        "type": "task",
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
        "type": "task",
        "id": "t-fill-text",
        "blocks": [
            {"type": "fill_text",
             "template": "Сила измеряется в ___u___.",
             "blanks": {"u": "ньютонах"},
             "bank": ["ньютонах", "джоулях"]},
        ],
    },
    "fill_table": {
        "type": "task",
        "id": "t-fill-table",
        "blocks": [
            {"type": "fill_table",
             "headers": ["t, с", "s, м"],
             "rows": [["0", "0"], ["1", {"answer": "5"}]]},
        ],
    },
    "plot": {
        "type": "task",
        "id": "t-plot",
        "blocks": [
            {"type": "plot", "x_label": "t, с", "y_label": "υ, м/с",
             "x_range": [0, 5], "y_range": [0, 10],
             "given": [{"points": [[0, 0]], "style": "solid"}],
             "answer": [{"points": [[0, 0], [4, 8]], "style": "solid"}]},
        ],
    },
    "true_false": {
        "type": "task",
        "id": "t-tf",
        "blocks": [
            {"type": "true_false", "statements": [
                {"text": "Скорость — вектор.", "answer": True},
                {"text": "Путь — вектор.", "answer": False},
            ]},
        ],
    },
    "rank": {
        "type": "task",
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
        "type": "task",
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
        "type": "task",
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
    # Приборы, семейства strip + column: линейка с бруском, мензурка и
    # термометр в row, динамометр с пустой шкалой (value не задан).
    "instruments_scales": {
        "type": "task",
        "id": "t-instr-scales",
        "blocks": [
            {"type": "text", "body": "Определите цену деления и показания приборов."},
            {"type": "instrument", "kind": "ruler", "unit": "см",
             "min": 0, "max": 10, "step": 0.1, "value": 6.4, "caption": "Линейка"},
            {"type": "row", "blocks": [
                {"type": "instrument", "kind": "cylinder", "unit": "мл",
                 "min": 0, "max": 250, "step": 10, "value": 175, "caption": "Мензурка"},
                {"type": "instrument", "kind": "thermometer", "unit": "°C",
                 "min": -10, "max": 50, "step": 1, "value": 21.5, "caption": "Термометр"},
                {"type": "instrument", "kind": "dynamometer", "unit": "Н",
                 "min": 0, "max": 4, "step": 0.1, "caption": "Динамометр"},
            ]},
            {"type": "open", "response": "lines:3", "answer": "V = 175 ± 5 мл"},
        ],
    },
    # Приборы, семейство dial: все пять стрелочных видов, с показанием
    # между штрихами и с пустой шкалой.
    "instruments_dials": {
        "type": "task",
        "id": "t-instr-dials",
        "blocks": [
            {"type": "row", "blocks": [
                {"type": "instrument", "kind": "ammeter", "unit": "А",
                 "min": 0, "max": 3, "step": 0.1, "value": 1.35, "caption": "Амперметр"},
                {"type": "instrument", "kind": "voltmeter", "unit": "В",
                 "min": 0, "max": 6, "step": 0.2, "value": 4.5, "caption": "Вольтметр"},
            ]},
            {"type": "row", "blocks": [
                {"type": "instrument", "kind": "manometer", "unit": "кПа",
                 "min": 0, "max": 400, "step": 10, "value": 260},
                {"type": "instrument", "kind": "scale_dial", "unit": "г",
                 "min": 0, "max": 1000, "step": 25, "value": 640},
                {"type": "instrument", "kind": "speedometer", "unit": "км/ч",
                 "min": 0, "max": 180, "step": 5},
            ]},
            {"type": "open", "response": "blank", "answer": "I = 1,35 ± 0,05 А"},
        ],
    },
    # row из двух part + чистые компоненты table и list.
    "row_and_components": {
        "type": "task",
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


# Минимальная спека standalone-визуала (`--visual`, standalone.py) на каждый
# подтип/семейство: ключ — суффикс golden-файла. Новый вид генератора
# добавляется сюда — golden-, структурный и эскейпинг-тесты standalone-SVG
# (test_standalone.py) подхватят его автоматически.
MINIMAL_VISUALS = {
    "graph-line": {
        "type": "graph", "x_label": "t, с", "y_label": "υ, м/с",
        "x_range": [0, 6], "y_range": [0, 12],
        "series": [
            {"label": "Тело 1", "points": [[0, 0], [5, 10]]},
            {"label": "Тело 2", "points": [[0, 10], [5, 2]], "style": "dashed"},
        ],
    },
    "graph-bar": {
        "type": "graph", "x_label": "№ опыта", "y_label": "F, Н",
        "x_range": [0, 5], "y_range": [0, 8], "chart_type": "bar",
        "series": [{"label": "Сила трения", "points": [[1, 2], [2, 4], [3, 6], [4, 7]]}],
    },
    "graph-scatter": {
        "type": "graph", "x_label": "m, кг", "y_label": "S, м<sup>2</sup>",
        "x_range": [0, 10], "y_range": [0, 40], "chart_type": "scatter",
        "series": [
            {"label": "Серия 1", "points": [[1, 3], [4, 15], [8, 33]]},
            {"label": "Серия 2", "points": [[2, 5], [6, 20]]},
        ],
    },
    "instrument-ruler": {
        "type": "instrument", "kind": "ruler", "unit": "см",
        "min": 0, "max": 10, "step": 0.1, "value": 6.4, "caption": "Линейка с бруском",
    },
    "instrument-cylinder": {
        "type": "instrument", "kind": "cylinder", "unit": "мл",
        "min": 0, "max": 250, "step": 10, "value": 175, "caption": "Мензурка",
    },
    "instrument-voltmeter": {
        "type": "instrument", "kind": "voltmeter", "unit": "В",
        "min": 0, "max": 6, "step": 0.2, "value": 4.5,
    },
    # Рычажные весы (всегда в равновесии): тело + гири с повтором (50+10+10).
    "instrument-balance": {
        "type": "instrument", "kind": "balance", "unit": "г",
        "min": 0, "max": 200, "step": 1, "value": 70, "weights": [50, 10, 10],
        "caption": "Рычажные весы",
    },
    # Нониус: value = 27 + 4·0,1 — совпадает 4-й штрих нониуса.
    "instrument-caliper": {
        "type": "instrument", "kind": "caliper", "unit": "мм",
        "min": 0, "max": 40, "step": 1, "vernier": 10, "value": 27.4,
        "caption": "Штангенциркуль",
    },
    # Полная круговая шкала: нуль и предел совпадают наверху, подписан предел.
    "instrument-stopwatch": {
        "type": "instrument", "kind": "stopwatch", "unit": "с",
        "min": 0, "max": 30, "step": 0.2, "value": 16.4,
        "caption": "Секундомер",
    },
    # Цифровое табло: step = дискретность, показание печатается с её числом
    # десятичных знаков.
    "instrument-digital": {
        "type": "instrument", "kind": "multimeter", "unit": "В",
        "min": 0, "max": 20, "step": 0.01, "value": 12.47,
        "caption": "Цифровой вольтметр",
    },
    # Регресс табло: step мельче сотых (0.001 → три знака показания;
    # fmt_num его обрезал до целого) и отрицательный min (разделитель
    # диапазона «…», чтобы минус не сливался с тире).
    "instrument-digital-fine": {
        "type": "instrument", "kind": "multimeter", "unit": "В",
        "min": -2, "max": 2, "step": 0.001, "value": 1.234,
        "caption": "Милливольтовый режим",
    },
    # Двухпредельный прибор (шаблон школьного J0407): двойная шкала на
    # одной дуге (внешняя −1…3, внутренняя −0.2…0.6 — заход в минус),
    # клеммы «−»/«0.6А»/«3А», класс точности.
    "instrument-multirange": {
        "type": "instrument", "kind": "ammeter", "unit": "А",
        "min": -1, "max": 3, "step": 0.1, "value": 1.85,
        "ranges": [0.6, 3], "accuracy_class": 2.5,
        "caption": "Двухпредельный амперметр",
    },
}
