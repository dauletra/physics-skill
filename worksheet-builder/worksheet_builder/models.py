"""Pydantic-модели схемы задания и meta.json — единственное представление
данных пакета: и валидация, и типизированное дерево, по которому работает
рендер (`components.py`/`questions.py`/`document.py`). Другого слоя данных
нет — параллельных классов с повторным парсингом сырых dict'ов не заводить.

Модели проверяют сырой JSON при загрузке: обязательные поля, закрытые
словари, кросс-инварианты — всё с `extra="forbid"`, так что опечатка в имени
поля — ошибка, а не молчаливое игнорирование. Текстовые поля хранят СЫРОЙ
авторский текст — экранирует рендер в точке интерполяции (см. правило
экранирования в references/task-schema.md).

Публичные точки: `parse_task()` / `parse_meta()` (возвращают модель;
ValueError перечисляет ВСЕ нарушения разом, каждое — с путём до блока) и
`emit_json_schema()`.

Формат пути в ошибке: `task-10 -> blocks[2] -> graph -> x_range: ...`
(ASCII-стрелка `->` намеренно: `→` роняет печать в cp1251-консоли Windows).
"""

import re
from collections.abc import Iterator, Sequence
from typing import Annotated, Literal, Optional, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    field_validator,
    model_validator,
)
from pydantic_core import ErrorDetails

from worksheet_builder.strings import LETTERS

BLANK_RE = re.compile(r"___(\w+)___")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


Number = Union[int, float]
Point = tuple[Number, Number]
Range = tuple[Number, Number]


def _check_range(name: str, value: Range) -> Range:
    lo, hi = value
    if not lo < hi:
        raise ValueError(f"{name} must be [min, max] with min < max, got [{lo}, {hi}]")
    return value


def _check_bar_baseline(chart_type: str, y_range: Range) -> None:
    # Столбик, растущий не от нуля, врёт о соотношении высот.
    if chart_type == "bar" and y_range[0] != 0:
        raise ValueError(
            f"chart_type 'bar' requires y_range to start at 0, got [{y_range[0]}, {y_range[1]}]"
        )


class SeriesModel(StrictModel):
    label: Optional[str] = None
    points: list[Point] = Field(min_length=1)
    style: Literal["solid", "dashed", "dotted"] = "solid"


# --- Чистые компоненты ---

class TextModel(StrictModel):
    type: Literal["text"]
    id: Optional[str] = None
    body: str


class TableModel(StrictModel):
    type: Literal["table"]
    id: Optional[str] = None
    headers: list[str] = Field(min_length=1)
    rows: list[list[str]] = Field(min_length=1)

    @model_validator(mode="after")
    def _rows_match_headers(self) -> "TableModel":
        for i, row in enumerate(self.rows):
            if len(row) != len(self.headers):
                raise ValueError(
                    f"rows[{i}] has {len(row)} cells, expected {len(self.headers)} (as in headers)"
                )
        return self


class GraphModel(StrictModel):
    type: Literal["graph"]
    id: Optional[str] = None
    x_label: str
    y_label: str
    x_range: Range
    y_range: Range
    chart_type: Literal["line", "bar", "scatter"] = "line"
    series: list[SeriesModel] = Field(default_factory=list)

    @field_validator("x_range")
    @classmethod
    def _x_range_valid(cls, v: Range) -> Range:
        return _check_range("x_range", v)

    @field_validator("y_range")
    @classmethod
    def _y_range_valid(cls, v: Range) -> Range:
        return _check_range("y_range", v)

    @model_validator(mode="after")
    def _bar_constraints(self) -> "GraphModel":
        # Столбики нескольких серий рисовались бы друг поверх друга.
        if self.chart_type == "bar" and len(self.series) > 1:
            raise ValueError(f"chart_type 'bar' supports a single series, got {len(self.series)}")
        _check_bar_baseline(self.chart_type, self.y_range)
        return self


class ListModel(StrictModel):
    type: Literal["list"]
    id: Optional[str] = None
    items: list[str] = Field(min_length=1)
    marker: Literal["none", "number", "letter"] = "none"
    columns: Literal["single", "two", "inline"] = "single"

    @model_validator(mode="after")
    def _letters_fit(self) -> "ListModel":
        if self.marker == "letter" and len(self.items) > len(LETTERS):
            raise ValueError(
                f"marker 'letter' supports at most {len(LETTERS)} items, got {len(self.items)}"
            )
        return self


InstrumentKind = Literal[
    "ruler", "cylinder", "thermometer", "dynamometer",
    "ammeter", "voltmeter", "manometer", "scale_dial", "speedometer",
    "stopwatch", "caliper", "balance",
    "multimeter", "digital_scale", "digital_stopwatch",
]

# Вид прибора -> семейство геометрии шкалы. Семейство выбирает и генератор
# SVG (instruments.py), и лимит числа делений ниже; новый прибор с уже
# существующей геометрией — это строка здесь + ветка оформления в своём
# семействе, без новой модели.
INSTRUMENT_FAMILIES: dict[
    str, Literal["strip", "column", "dial", "clock", "vernier", "balance", "digital"]
] = {
    "ruler": "strip",
    "cylinder": "column",
    "thermometer": "column",
    "dynamometer": "column",
    "ammeter": "dial",
    "voltmeter": "dial",
    "manometer": "dial",
    "scale_dial": "dial",
    "speedometer": "dial",
    "stopwatch": "clock",
    "caliper": "vernier",
    "balance": "balance",
    "multimeter": "digital",
    "digital_scale": "digital",
    "digital_stopwatch": "digital",
}

# Читаемость: слишком плотные штрихи сливаются после масштабирования под
# целевую ширину семейства. Линейка терпит миллиметровую плотность,
# столбик и дуга — нет; полный круг секундомера (clock) вмещает больше
# дуги в 120°. У цифрового табло штрихов нет — лимит только технический
# (step здесь — дискретность, а не расстояние между штрихами).
# У штангенциркуля лимит держит читаемость нониуса: шкала — фрагмент
# штанги (обычно 0–40 мм), иначе штрихи нониуса сольются. У весов и табло
# штрихов нет — лимит только технический (step там — наименьшая гиря и
# дискретность соответственно).
_MAX_DIVISIONS = {
    "strip": 150, "column": 60, "dial": 60, "clock": 150,
    "vernier": 40, "balance": 10**6, "digital": 10**6,
}

# Классы точности по ГОСТ 8.401 — закрытый ряд; произвольное число — ошибка,
# а не «какой-то класс». Рисуются на шкале стрелочного прибора; задачи на
# приведённую погрешность (Δ = класс × предел / 100) — instruments.md.
ACCURACY_CLASSES = (0.05, 0.1, 0.2, 0.5, 1.0, 1.5, 2.5, 4.0)

# Виды с клеммами: только у них осмысленны многопредельные `ranges`.
_ELECTRIC_KINDS = ("ammeter", "voltmeter")


class InstrumentModel(StrictModel):
    type: Literal["instrument"]
    id: Optional[str] = None
    kind: InstrumentKind
    unit: str = Field(min_length=1)
    min: Number
    max: Number
    # Цена деления — всегда явная: это педагогическое данное задачи,
    # а не производная представления.
    step: Number = Field(gt=0)
    value: Optional[Number] = None
    caption: Optional[str] = None
    # Метрология (учебник погрешностей): класс точности печатается на шкале;
    # двухпредельный прибор (`ranges`, ровно два предела) несёт двойную
    # шкалу на одной дуге — min/max/step описывают внешнюю шкалу большего
    # предела (и value в её единицах; min <= 0, отрицательный min — заход
    # шкалы в минус), внутренняя получается умножением на отношение
    # пределов; клеммы «−» и по одной на предел, без выделения «включённой»
    # (куда воткнут провод — текст условия, не рисунок).
    accuracy_class: Optional[Number] = None
    ranges: Optional[list[Number]] = Field(default=None, min_length=2, max_length=2)
    # Штангенциркуль: число делений нониуса (точность отсчёта = step /
    # vernier: 10 -> 0,1 мм; 20 -> 0,05 мм). Не задан у caliper — считается 10.
    vernier: Optional[Literal[10, 20]] = None
    # Рычажные весы (balance): гири на правой чашке (повторы разрешены);
    # value — масса тела на левой; step — наименьшая гиря набора
    # (погрешность весов), max — предел взвешивания. Весы рисуются всегда
    # в равновесии: рисунок — постановка задачи, согласованность масс —
    # дело условия, а не валидатора.
    weights: Optional[list[Number]] = Field(default=None, min_length=1, max_length=4)

    @model_validator(mode="after")
    def _scale_valid(self) -> "InstrumentModel":
        if not self.min < self.max:
            raise ValueError(f"min/max must satisfy min < max, got [{self.min}, {self.max}]")
        divisions = (self.max - self.min) / self.step
        if abs(divisions - round(divisions)) > 1e-6 * max(divisions, 1):
            raise ValueError(
                f"step {self.step} must divide the scale range exactly, "
                f"got (max - min) / step = {divisions}"
            )
        limit = _MAX_DIVISIONS[INSTRUMENT_FAMILIES[self.kind]]
        if not 2 <= round(divisions) <= limit:
            raise ValueError(
                f"scale needs 2..{limit} divisions for kind {self.kind!r}, "
                f"got {round(divisions)}"
            )
        # Кратность value цене деления НЕ проверяется намеренно: показание
        # между штрихами — суть задач на погрешность отсчёта.
        if self.value is not None and not (self.min <= self.value <= self.max):
            raise ValueError(f"value {self.value} is outside the scale [{self.min}, {self.max}]")
        self._metrology_valid()
        return self

    def _metrology_valid(self) -> None:
        # Цифровое табло не показывает «между штрихами»: показание всегда
        # кратно дискретности (step). У аналоговых шкал — наоборот, см.
        # комментарий про кратность в _scale_valid.
        if INSTRUMENT_FAMILIES[self.kind] == "digital" and self.value is not None:
            offset = (self.value - self.min) / self.step
            if abs(offset - round(offset)) > 1e-6:
                raise ValueError(
                    f"digital display value must be a multiple of step {self.step}, "
                    f"got {self.value}"
                )
        if self.accuracy_class is not None:
            if INSTRUMENT_FAMILIES[self.kind] != "dial":
                raise ValueError(
                    f"accuracy_class is only drawn on dial instruments, not on {self.kind!r}"
                )
            if not any(abs(self.accuracy_class - c) < 1e-9 for c in ACCURACY_CLASSES):
                raise ValueError(
                    f"accuracy_class must be one of {list(ACCURACY_CLASSES)}, "
                    f"got {self.accuracy_class}"
                )
        if self.ranges is not None:
            if self.kind not in _ELECTRIC_KINDS:
                raise ValueError(
                    "ranges (a dual-scale instrument) are only supported for "
                    f"{'/'.join(_ELECTRIC_KINDS)}, not {self.kind!r}"
                )
            if any(r <= 0 for r in self.ranges):
                raise ValueError(f"ranges must be positive, got {self.ranges}")
            if sorted(set(self.ranges)) != list(self.ranges):
                raise ValueError(f"ranges must be strictly increasing, got {self.ranges}")
            # Физическая корректность двойной шкалы: обе шкалы — одна дуга.
            # Отрицательный min — заход шкалы в минус (как −1/−0.2 у J0407);
            # подписи обеих шкал продолжаются влево от нуля тем же правилом.
            if self.min > 0:
                raise ValueError(
                    f"a dual-scale instrument must start at 0 or below "
                    f"(negative overrun), got min {self.min}"
                )
            if abs(self.max - self.ranges[-1]) > 1e-9:
                raise ValueError(
                    f"max must equal the larger range {self.ranges[-1]} "
                    f"(min/max/step describe the outer scale), got max {self.max}"
                )
            inner_step = self.step * self.ranges[0] / self.ranges[-1]
            if abs(inner_step * 100 - round(inner_step * 100)) > 1e-6:
                raise ValueError(
                    f"ranges {self.ranges} give a non-round inner scale: its step would be "
                    f"{inner_step} (outer step {self.step} x {self.ranges[0]}/{self.ranges[-1]}); "
                    "labels are readable up to 2 decimal places"
                )
        if self.kind == "caliper":
            v = self.vernier or 10
            precision = self.step / v
            if self.value is not None:
                k = (self.value - self.min) / precision
                # Кратность точности нониуса обязательна: иначе совпадающий
                # штрих не определён и рисунок неоднозначен.
                if abs(k - round(k)) > 1e-6:
                    raise ValueError(
                        f"caliper value must be a multiple of the vernier precision "
                        f"{precision} (step {self.step} / {v} divisions), got {self.value}"
                    )
                fit_max = self.max - (v - 1) * self.step
                if self.value > fit_max + 1e-9:
                    raise ValueError(
                        f"vernier scale must fit on the bar: value <= {fit_max} "
                        f"(max - {v - 1}*step), got {self.value}"
                    )
        elif self.vernier is not None:
            raise ValueError(f"vernier is only supported for caliper, not {self.kind!r}")
        if self.kind == "balance":
            if self.min != 0:
                raise ValueError(f"balance scale must start at 0, got min {self.min}")
            if self.weights is not None:
                for i, wt in enumerate(self.weights):
                    if wt <= 0:
                        raise ValueError(f"weights[{i}] must be positive, got {wt}")
                    ratio = wt / self.step
                    # step — наименьшая гиря набора: любая гиря ей кратна,
                    # иначе step не является единицей разновеса.
                    if abs(ratio - round(ratio)) > 1e-6 or wt < self.step - 1e-9:
                        raise ValueError(
                            f"weights[{i}] = {wt} must be a multiple of step {self.step} "
                            "(step is the smallest weight of the set)"
                        )
                total = sum(self.weights)
                if total > self.max + 1e-9:
                    raise ValueError(
                        f"weights sum {total} exceeds the weighing limit max = {self.max}"
                    )
        elif self.weights is not None:
            raise ValueError(f"weights are only supported for balance, not {self.kind!r}")


# --- Вопросы (конверт: type + опциональные id/explanation) ---

class QuestionEnvelope(StrictModel):
    id: Optional[str] = None
    explanation: Optional[str] = None


class OpenModel(QuestionEnvelope):
    type: Literal["open"]
    response: str = "none"
    answer: Optional[str] = None

    @field_validator("response")
    @classmethod
    def _response_valid(cls, v: str) -> str:
        if v.startswith("lines:"):
            suffix = v.split(":", 1)[1]
            if not (suffix.isdigit() and int(suffix) > 0):
                raise ValueError(f"response 'lines:N' requires positive integer N, got {v!r}")
            return v
        if v not in ("blank", "none"):
            raise ValueError(f"response must be 'lines:N', 'blank' or 'none', got {v!r}")
        return v


class ChoiceOptionModel(StrictModel):
    text: str
    correct: bool = False


class ChoiceModel(QuestionEnvelope):
    type: Literal["choice"]
    select: Literal["single", "multiple"] = "single"
    options: list[ChoiceOptionModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _correct_count(self) -> "ChoiceModel":
        n_correct = sum(1 for o in self.options if o.correct)
        if self.select == "single" and n_correct != 1:
            raise ValueError(f"select='single' requires exactly one correct option, got {n_correct}")
        if self.select == "multiple" and n_correct == 0:
            raise ValueError("select='multiple' requires at least one correct option")
        return self


class MatchLeftModel(StrictModel):
    text: str
    match: str


class MatchRightModel(StrictModel):
    id: str = Field(min_length=1)
    text: str


class MatchModel(QuestionEnvelope):
    type: Literal["match"]
    left: list[MatchLeftModel] = Field(min_length=1)
    right: list[MatchRightModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _refs_valid(self) -> "MatchModel":
        ids = [r.id for r in self.right]
        if len(set(ids)) != len(ids):
            raise ValueError(f"right ids must be unique, got {ids}")
        if len(self.right) > len(LETTERS):
            raise ValueError(
                f"right supports at most {len(LETTERS)} items (letter markers), got {len(self.right)}"
            )
        for i, item in enumerate(self.left):
            if item.match not in set(ids):
                raise ValueError(f"left[{i}].match {item.match!r} not found among right ids {ids}")
        return self


class FillTextModel(QuestionEnvelope):
    type: Literal["fill_text"]
    template: str
    blanks: dict[str, str] = Field(default_factory=dict)
    bank: Optional[list[str]] = None

    @model_validator(mode="after")
    def _placeholders_match(self) -> "FillTextModel":
        placeholders = set(BLANK_RE.findall(self.template))
        if placeholders != set(self.blanks.keys()):
            raise ValueError(
                f"template placeholders {placeholders or '{}'} != blanks keys {set(self.blanks.keys()) or '{}'}"
            )
        return self


class BlankCellModel(StrictModel):
    answer: str


class FillTableModel(QuestionEnvelope):
    type: Literal["fill_table"]
    headers: list[str] = Field(min_length=1)
    rows: list[list[Union[str, BlankCellModel]]] = Field(min_length=1)
    bank: Optional[list[str]] = None

    @model_validator(mode="after")
    def _rows_valid(self) -> "FillTableModel":
        has_blank = False
        for i, row in enumerate(self.rows):
            if len(row) != len(self.headers):
                raise ValueError(
                    f"rows[{i}] has {len(row)} cells, expected {len(self.headers)} (as in headers)"
                )
            has_blank = has_blank or any(isinstance(c, BlankCellModel) for c in row)
        if not has_blank:
            raise ValueError("at least one cell must be a blank ({'answer': ...})")
        return self


class PlotModel(QuestionEnvelope):
    type: Literal["plot"]
    x_label: str
    y_label: str
    x_range: Range
    y_range: Range
    chart_type: Literal["line", "bar", "scatter"] = "line"
    given: Optional[list[SeriesModel]] = None
    answer: list[SeriesModel] = Field(min_length=1)

    @field_validator("x_range")
    @classmethod
    def _x_range_valid(cls, v: Range) -> Range:
        return _check_range("x_range", v)

    @field_validator("y_range")
    @classmethod
    def _y_range_valid(cls, v: Range) -> Range:
        return _check_range("y_range", v)

    @model_validator(mode="after")
    def _bar_constraints(self) -> "PlotModel":
        if self.chart_type == "bar" and (len(self.answer) > 1 or len(self.given or []) > 1):
            raise ValueError("chart_type 'bar' supports a single series in 'given' and in 'answer'")
        _check_bar_baseline(self.chart_type, self.y_range)
        return self


class StatementModel(StrictModel):
    text: str
    answer: bool


class TrueFalseModel(QuestionEnvelope):
    type: Literal["true_false"]
    statements: list[StatementModel] = Field(min_length=1)


class RankItemModel(StrictModel):
    text: str
    position: int


class RankModel(QuestionEnvelope):
    type: Literal["rank"]
    items: list[RankItemModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _positions_valid(self) -> "RankModel":
        positions = sorted(item.position for item in self.items)
        if positions != list(range(1, len(self.items) + 1)):
            raise ValueError(f"positions must be a permutation of 1..{len(self.items)}, got {positions}")
        return self


class ClassifyItemModel(StrictModel):
    text: str
    category: str


class ClassifyModel(QuestionEnvelope):
    type: Literal["classify"]
    categories: list[str] = Field(min_length=1)
    items: list[ClassifyItemModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _categories_valid(self) -> "ClassifyModel":
        if len(set(self.categories)) != len(self.categories):
            raise ValueError(f"categories must be unique, got {self.categories}")
        for i, item in enumerate(self.items):
            if item.category not in self.categories:
                raise ValueError(
                    f"items[{i}].category {item.category!r} not found in categories {self.categories}"
                )
        return self


# --- Контейнеры ---

ComponentModel = Union[TextModel, TableModel, GraphModel, ListModel, InstrumentModel]
QuestionModel = Union[
    OpenModel, ChoiceModel, MatchModel, FillTextModel, FillTableModel,
    PlotModel, TrueFalseModel, RankModel, ClassifyModel,
]
QUESTION_MODEL_TYPES = (
    OpenModel, ChoiceModel, MatchModel, FillTextModel, FillTableModel,
    PlotModel, TrueFalseModel, RankModel, ClassifyModel,
)

# Один плоский дискриминатор `type` на всё дерево. Структурно union допускает
# любой блок где угодно; контекстные запреты (вложенные part/row, состав
# соседей) выражены model_validator-ами ниже — с человеческими сообщениями
# вместо загадочного несовпадения тега.
AnyBlockModel = Annotated[
    Union[ComponentModel, QuestionModel, "PartModel", "RowModel"],
    Field(discriminator="type"),
]


def iter_flat_models(blocks: "list[AnyBlockModel]") -> "Iterator[AnyBlockModel]":
    """Сплющенный обход: `row` прозрачен — его дети считаются сиблингами на
    уровне родителя. По этому обходу считаются и инварианты состава (здесь),
    и раздача букв подзаданий (document.py) — раскладка не может изменить
    смысл/нумерацию."""
    for block in blocks:
        if isinstance(block, RowModel):
            yield from block.blocks
        else:
            yield block


class RowModel(StrictModel):
    type: Literal["row"]
    id: Optional[str] = None
    blocks: list[AnyBlockModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _no_nested_rows(self) -> "RowModel":
        if any(isinstance(b, RowModel) for b in self.blocks):
            raise ValueError("nested rows are not supported")
        return self


class PartModel(StrictModel):
    type: Literal["part"]
    id: Optional[str] = None
    label: Optional[str] = None
    points: Optional[Number] = Field(default=None, gt=0)
    blocks: list[AnyBlockModel] = Field(min_length=1)

    @field_validator("label")
    @classmethod
    def _label_is_letter(cls, v: Optional[str]) -> Optional[str]:
        # Явный label живёт в том же перечислительном ряду, что и авто-буквы:
        # иначе на листе смешались бы две системы нумерации подзаданий.
        if v is not None and not (len(v) == 1 and v in LETTERS):
            raise ValueError(f"label must be a single letter from '{LETTERS}', got {v!r}")
        return v

    @model_validator(mode="after")
    def _composition(self) -> "PartModel":
        flat = list(iter_flat_models(self.blocks))
        if any(isinstance(b, PartModel) for b in flat):
            raise ValueError("nested parts are not supported")
        questions = [b for b in flat if isinstance(b, QUESTION_MODEL_TYPES)]
        if len(questions) != 1:
            raise ValueError(f"part must contain exactly one question, got {len(questions)}")
        return self


class TaskModel(StrictModel):
    id: str
    points: Optional[Number] = Field(default=None, gt=0)
    blocks: list[AnyBlockModel] = Field(min_length=1)

    @model_validator(mode="after")
    def _composition(self) -> "TaskModel":
        flat = list(iter_flat_models(self.blocks))
        parts = [b for b in flat if isinstance(b, PartModel)]
        questions = [b for b in flat if isinstance(b, QUESTION_MODEL_TYPES)]
        if parts and questions:
            raise ValueError("'part' and a bare question cannot be siblings - wrap every question in a part")
        if not parts and len(questions) > 1:
            raise ValueError("more than one bare question - wrap each question in its own 'part'")
        if len(parts) > len(LETTERS):
            raise ValueError(f"at most {len(LETTERS)} parts per task (letter labels), got {len(parts)}")
        labels = [p.label for p in parts if p.label]
        dupes = sorted({lbl for lbl in labels if labels.count(lbl) > 1})
        if dupes:
            raise ValueError(f"explicit part labels must be unique, duplicated: {dupes}")
        self._check_unique_ids()
        return self

    def _check_unique_ids(self) -> None:
        seen: dict[str, str] = {}

        def walk(blocks: list, path: str) -> None:
            for i, block in enumerate(blocks):
                block_path = f"{path}[{i}]"
                block_id = getattr(block, "id", None)
                if block_id:
                    if block_id in seen:
                        raise ValueError(
                            f"duplicate block id {block_id!r} at {block_path} (already used at {seen[block_id]})"
                        )
                    seen[block_id] = block_path
                if isinstance(block, (PartModel, RowModel)):
                    walk(block.blocks, f"{block_path}.blocks")

        walk(self.blocks, "blocks")


class MetaModel(StrictModel):
    title: str = ""
    subject: str = ""
    grade: str = ""
    school: str = ""
    date: str = ""
    instructions: Optional[str] = None
    order: Optional[list[str]] = None

    @field_validator("grade", mode="before")
    @classmethod
    def _grade_to_str(cls, v: object) -> str:
        return str(v) if v is not None else ""

    @field_validator("order")
    @classmethod
    def _order_unique(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is not None and len(set(v)) != len(v):
            dupes = sorted({x for x in v if v.count(x) > 1})
            raise ValueError(f"order contains duplicates: {dupes}")
        return v


# --- Документ (режим --document): произвольный текст + визуалы, без вопросов ---

class HeadingModel(StrictModel):
    """Подзаголовок раздела — только для документов: в заданиях листа своей
    иерархии заголовков нет (номер и буквы подзаданий рисует рендер)."""
    type: Literal["heading"]
    id: Optional[str] = None
    text: str


DocumentLeafModel = Union[ComponentModel, HeadingModel]


class DocumentRowModel(StrictModel):
    """`row` документа: те же равные колонки (CSS `.task-row`), но дети —
    только компоненты/заголовки. Отдельная модель, а не RowModel листа,
    чтобы вопросы и part в документе были невыразимы структурно (заодно
    невыразим и вложенный row)."""
    type: Literal["row"]
    id: Optional[str] = None
    blocks: list[Annotated[DocumentLeafModel, Field(discriminator="type")]] = Field(min_length=1)


DocumentBlockModel = Annotated[
    Union[DocumentLeafModel, DocumentRowModel],
    Field(discriminator="type"),
]

# Типы блоков листа, которым нет места в документе: по ним before-валидатор
# даёт человеческую ошибку вместо загадочного "unknown block type".
_DOC_FORBIDDEN_TYPES = frozenset({
    "part", "open", "choice", "match", "fill_text", "fill_table",
    "plot", "true_false", "rank", "classify",
})


def _reject_worksheet_block(block: object, path: str) -> None:
    if not isinstance(block, dict):
        return
    btype = block.get("type")
    if btype in _DOC_FORBIDDEN_TYPES:
        raise ValueError(
            f"{path}: block type {btype!r} is not allowed in a document "
            "(questions and parts belong to worksheet tasks)"
        )
    if btype == "row":
        children = block.get("blocks")
        for i, child in enumerate(children if isinstance(children, list) else []):
            _reject_worksheet_block(child, f"{path}.blocks[{i}]")


class DocumentModel(StrictModel):
    """Документ (конспект, теория, текст с иллюстрациями): заголовок + блоки
    из чистых компонентов. Вопросов нет — нет и режимов student/teacher."""
    title: str = ""
    blocks: list[DocumentBlockModel] = Field(min_length=1)

    @model_validator(mode="before")
    @classmethod
    def _no_worksheet_blocks(cls, data: object) -> object:
        if isinstance(data, dict):
            blocks = data.get("blocks")
            for i, block in enumerate(blocks if isinstance(blocks, list) else []):
                _reject_worksheet_block(block, f"blocks[{i}]")
        return data

    @model_validator(mode="after")
    def _unique_ids(self) -> "DocumentModel":
        seen: dict[str, str] = {}
        for i, block in enumerate(self.blocks):
            flat: list[tuple[str, object]] = [(f"blocks[{i}]", block)]
            if isinstance(block, DocumentRowModel):
                flat += [
                    (f"blocks[{i}].blocks[{j}]", child)
                    for j, child in enumerate(block.blocks)
                ]
            for path, b in flat:
                block_id = getattr(b, "id", None)
                if block_id:
                    if block_id in seen:
                        raise ValueError(
                            f"duplicate block id {block_id!r} at {path} "
                            f"(already used at {seen[block_id]})"
                        )
                    seen[block_id] = path
        return self


# --- Адаптер ошибок и публичные точки входа ---

def _format_loc(loc: Sequence[int | str]) -> str:
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int):
            if parts:
                parts[-1] += f"[{item}]"
            else:
                parts.append(f"[{item}]")
        else:
            parts.append(str(item))
    return " -> ".join(parts)


def _format_error(err: ErrorDetails) -> str:
    err_type = err.get("type", "")
    loc = err.get("loc", ())
    if err_type == "union_tag_invalid":
        tag = err.get("ctx", {}).get("tag")
        return f"{_format_loc(loc)}: unknown block type {tag!r}"
    if err_type == "union_tag_not_found":
        return f"{_format_loc(loc)}: block has no 'type' field"
    if err_type == "missing":
        return f"{_format_loc(loc[:-1])}: missing required field {str(loc[-1])!r}"
    if err_type == "extra_forbidden":
        return f"{_format_loc(loc[:-1])}: unknown field {str(loc[-1])!r}"
    msg = err.get("msg", "")
    msg = msg.removeprefix("Value error, ")
    return f"{_format_loc(loc)}: {msg}" if loc else msg


def format_validation_error(prefix: str, exc: ValidationError) -> str:
    lines = [f"{prefix} -> {_format_error(e)}" for e in exc.errors()]
    return "\n".join(lines)


def parse_task(data: object) -> TaskModel:
    """Проверяет сырой dict задания и возвращает типизированную модель;
    ValueError перечисляет ВСЕ нарушения, каждое — с путём до блока."""
    task_id = data.get("id", "<no id>") if isinstance(data, dict) else "<not an object>"
    try:
        return TaskModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(format_validation_error(str(task_id), exc)) from None


def parse_meta(data: object) -> MetaModel:
    try:
        return MetaModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(format_validation_error("meta.json", exc)) from None


# Спека режима `--visual` (cli.py) — ровно один визуальный блок листа, по той
# же схеме и с теми же инвариантами, что и внутри задания. Новый визуальный
# компонент добавляется в этот union — и standalone-рендер его видит.
VisualModel = Union[GraphModel, InstrumentModel]
_VISUAL_ADAPTER: TypeAdapter[VisualModel] = TypeAdapter(
    Annotated[VisualModel, Field(discriminator="type")]
)


def parse_visual(data: object, name: str = "visual") -> VisualModel:
    """Проверяет сырой dict спеки `--visual` и возвращает модель визуального
    блока; ValueError — в том же формате с путём до поля, что и parse_task."""
    try:
        return _VISUAL_ADAPTER.validate_python(data)
    except ValidationError as exc:
        raise ValueError(format_validation_error(name, exc)) from None


def parse_document(data: object, name: str = "document") -> DocumentModel:
    """Проверяет сырой dict документа (`--document`); ValueError перечисляет
    все нарушения разом, каждое — с путём до блока."""
    try:
        return DocumentModel.model_validate(data)
    except ValidationError as exc:
        raise ValueError(format_validation_error(name, exc)) from None


def emit_json_schema() -> dict:
    """JSON Schema всех корневых моделей — для автокомплита в редакторе
    (`python -m worksheet_builder --emit-schema`)."""
    return {
        "meta": MetaModel.model_json_schema(),
        "task": TaskModel.model_json_schema(),
        "document": DocumentModel.model_json_schema(),
    }
