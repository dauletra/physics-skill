"""Fill in the blanks, carried by a table.

The payload is deliberately the shape of the `table` component — `headers`
and `rows` — with some cells replaced by `{"answer": …}`. One visual form,
one set of field names.
"""

from __future__ import annotations

from typing import Literal, Optional, Union

from physics_svg.document.html import bank_list, blank_cell, table_html
from physics_svg.document.questions.registry import register
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec


@spec
class BlankCellSpec:
    """Ячейка-пропуск: ответ инлайн, на месте содержимого."""

    answer: str


Cell = Union[str, BlankCellSpec]


@spec
class FillTableSpec:
    """Таблица с пропущенными ячейками."""

    type: Literal["fill_table"]
    headers: list[str] = field(min_items=1)
    rows: list[list[Cell]] = field(
        min_items=1, doc="Строки: строка-текст или пропуск {\"answer\": \"…\"}"
    )
    id: Optional[str] = None
    explanation: Optional[str] = None
    bank: Optional[list[str]] = field(default=None, doc="Слова для выбора, если нужен банк")

    def check(self) -> None:
        has_blank = False
        for i, row in enumerate(self.rows):
            if len(row) != len(self.headers):
                raise Invalid(
                    f"в строке {i} {len(row)} ячеек, а колонок {len(self.headers)}", field="rows"
                )
            has_blank = has_blank or any(not isinstance(cell, str) for cell in row)
        if not has_blank:
            raise Invalid(
                "хотя бы одна ячейка должна быть пропуском {\"answer\": …}", field="rows"
            )


def body(model: FillTableSpec) -> str:
    rows = [
        [esc(cell) if isinstance(cell, str) else blank_cell() for cell in row]
        for row in model.rows
    ]
    table = table_html([esc(header) for header in model.headers], rows)
    return bank_list(model.bank) + table if model.bank else table


def answer(model: FillTableSpec) -> str:
    # Blank values in reading order.
    values = [
        cell.answer for row in model.rows for cell in row if not isinstance(cell, str)
    ]
    return esc("; ".join(values))


register(
    tag="fill_table", title="Пропуски в таблице", model=FillTableSpec, body=body, answer=answer,
    module=__name__,
)
