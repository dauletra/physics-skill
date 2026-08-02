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

from physics_svg.document.html import blank, div, inline_blank, list_html, table_html
from physics_svg.document.strings import LETTERS, t
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec

#: A run of underscores in author text is a ruled space, as wide as it was
#: typed. Three is the shortest run that cannot be a typo or an em dash typed
#: by hand.
BLANK_RUN = re.compile(r"_{3,}")

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


# --- rendering ----------------------------------------------------------


def render_text(model: TextSpec) -> str:
    # Escaping first, then the ruling: the blank is markup the renderer adds,
    # and it must not be escaped along with the author's text.
    body = BLANK_RUN.sub(lambda run: inline_blank(len(run.group())), esc(model.body))
    return f"<p>{body}</p>"


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
    return div(f"doc-heading level-{model.level}", esc(model.text))


def render_divider(model: DividerSpec) -> str:
    return '<hr class="doc-divider">'
