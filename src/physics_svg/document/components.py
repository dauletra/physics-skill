"""Components that are not illustrations: text, table, list, answer line.

A component is pure display. It knows nothing about a question, an answer or
whether something is correct — there are no `answer` or `correct` fields here
and there never will be. The converse holds too, and matters more than it
looks: **the place a student writes is a component**, not a field on a
question. `answer_line` and `paper` are neighbours of the question, so the
same question can be asked with three lines under it, with graph paper, or
with nothing at all, without touching the question itself.

The illustrations (`graph`, `instrument`, `paper`) are components too — they
come from the visual registry rather than from this module.
"""

from __future__ import annotations

import re
from typing import Literal, Optional

from physics_svg.document.inline import parse_inline
from physics_svg.document.layout import (
    Bullets,
    Grid,
    Heading,
    Item,
    Line,
    Para,
    Rule,
    Run,
    Slot,
)
from physics_svg.document.strings import LETTERS, t
from physics_svg.schema import Invalid, field, spec

#: The `fill_text` gap, recognised here only in order to be refused.
NAMED_BLANK = re.compile(r"_{3,}[^\W_]\w*_{3,}")


@spec
class TextSpec:
    """Абзац текста: условие задачи, объяснение, определение."""

    type: Literal["text"]
    body: str = field(
        doc="Текст абзаца; допустимы <sup>/<sub>, формулы KaTeX в $…$ и место "
        "для записи — три подчёркивания и больше, длиной в линию: «Дата: ______»"
    )
    id: Optional[str] = None

    def check(self) -> None:
        # `___имя___` is the syntax of a gap that carries an answer. In a
        # component there is nowhere for that answer to go, and the sheet would
        # print two rules around the name instead of one blank.
        if NAMED_BLANK.search(self.body):
            raise Invalid(
                "пропуск с именем '___имя___' бывает только в вопросе 'fill_text'; "
                "место для записи в тексте — просто подчёркивания",
                field="body",
            )


@spec
class TableSpec:
    """Таблица с подписанными колонками."""

    type: Literal["table"]
    headers: list[str] = field(min_items=1, doc="Заголовки колонок")
    rows: list[list[str]] = field(min_items=1, doc="Строки: по ячейке на колонку")
    id: Optional[str] = None

    def check(self) -> None:
        for i, row in enumerate(self.rows):
            if len(row) != len(self.headers):
                raise Invalid(
                    f"в строке {i} {len(row)} ячеек, а колонок {len(self.headers)}",
                    field="rows",
                )


@spec
class ListSpec:
    """Список пунктов."""

    type: Literal["list"]
    items: list[str] = field(min_items=1, doc="Пункты списка")
    id: Optional[str] = None
    marker: Literal["none", "number", "letter"] = "none"
    columns: Literal["single", "two", "inline"] = "single"

    def check(self) -> None:
        if self.marker == "letter" and len(self.items) > len(LETTERS):
            raise Invalid(
                f"буквенный маркер рассчитан не больше чем на {len(LETTERS)} пунктов, "
                f"получено {len(self.items)}",
                field="items",
            )


@spec
class AnswerLineSpec:
    """Строка «Ответ: ______» под короткий ответ.

    Отдельный компонент, а не разлиновка `paper`: это не площадь, а строчка
    в потоке текста, и геометрии у неё нет.
    """

    type: Literal["answer_line"]
    id: Optional[str] = None


@spec
class HeadingSpec:
    """Заголовок документа или его раздела.

    Внутри задания заголовков нет — там иерархию рисуют номер задания и
    буквы подзаданий.
    """

    type: Literal["heading"]
    text: str = field(doc="Текст заголовка")
    id: Optional[str] = None
    level: Literal[1, 2] = field(default=2, doc="1 — название документа, 2 — раздел")


@spec
class DividerSpec:
    """Горизонтальная линия между частями документа.

    Шапка, отделённая от заданий, — её первый случай, но разделитель ничего
    не знает про шапку: это просто линия там, где автор её поставил.
    """

    type: Literal["divider"]
    id: Optional[str] = None


# --- layout -------------------------------------------------------------


def build_text(model: TextSpec) -> Para:
    # `blanks=True`: a run of underscores in a paragraph is a place to write.
    # In a `fill_text` template it is not — there a gap carries a name.
    return Para(parse_inline(model.body, blanks=True))


def build_table(model: TableSpec) -> Grid:
    return Grid(
        tuple(parse_inline(header) for header in model.headers),
        tuple(tuple(parse_inline(cell) for cell in row) for row in model.rows),
    )


def build_list(model: ListSpec) -> Bullets:
    items: tuple[Item, ...] = tuple(parse_inline(item) for item in model.items)
    return Bullets(items, model.marker, model.columns)


def build_answer_line(model: AnswerLineSpec) -> Line:
    return Line((Run(f'{t("answer_label")} '), Slot()))


def build_heading(model: HeadingSpec) -> Heading:
    return Heading(model.level, parse_inline(model.text))


def build_divider(model: DividerSpec) -> Rule:
    return Rule()
