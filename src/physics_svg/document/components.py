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

from typing import Literal, Optional

from physics_svg.document.html import blank, div, list_html, table_html
from physics_svg.document.strings import LETTERS, t
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec


@spec
class TextSpec:
    """Абзац текста: условие задачи, объяснение, определение."""

    type: Literal["text"]
    body: str = field(doc="Текст абзаца; допустимы <sup>/<sub> и формулы KaTeX в $…$")
    id: Optional[str] = None


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
    """Подзаголовок раздела документа.

    Внутри задания заголовков нет — там иерархию рисуют номер задания и
    буквы подзаданий.
    """

    type: Literal["heading"]
    text: str = field(doc="Текст подзаголовка")
    id: Optional[str] = None


# --- rendering ----------------------------------------------------------


def render_text(model: TextSpec) -> str:
    return f"<p>{esc(model.body)}</p>"


def render_table(model: TableSpec) -> str:
    return table_html(
        [esc(header) for header in model.headers],
        [[esc(cell) for cell in row] for row in model.rows],
    )


def render_list(model: ListSpec) -> str:
    return list_html([esc(item) for item in model.items], model.marker, model.columns)


def render_answer_line(model: AnswerLineSpec) -> str:
    return f'<div>{t("answer_label")} {blank()}</div>'


def render_heading(model: HeadingSpec) -> str:
    return div("doc-heading", esc(model.text))
