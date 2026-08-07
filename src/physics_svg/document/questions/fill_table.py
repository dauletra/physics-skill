"""Fill in the blanks, carried by a table.

The payload is deliberately the shape of the `table` component — `headers`
and `rows` — with some cells replaced by `{"answer": …}`. One visual form,
one set of field names.
"""

from __future__ import annotations

from typing import Literal, Optional, Union

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.domain import Domain
from physics_svg.document.inline import parse_inline
from physics_svg.document.layout import Bank, Block, Gap, Grid, Stack, Text
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import t
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

    @property
    def domain(self) -> Optional[Domain]:
        """The word bank, when there is one — the same vocabulary `fill_text`
        offers, printed by the same line."""
        return None if self.bank is None else Domain(self.bank, "bank")

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
        # A bank that misses a correct value makes the table unfillable.
        if self.domain is not None:
            self.domain.check()
            for i, row in enumerate(self.rows):
                for cell in row:
                    if not isinstance(cell, str):
                        self.domain.check_member(cell.answer, field="rows", index=i)


def body(model: FillTableSpec) -> Block:
    rows: tuple[tuple[Text, ...], ...] = tuple(
        tuple(parse_inline(cell) if isinstance(cell, str) else (Gap(),) for cell in row)
        for row in model.rows
    )
    table = Grid(tuple(parse_inline(header) for header in model.headers), rows)
    if not model.bank:
        return table
    bank = Bank(t("bank_label"), tuple(parse_inline(word) for word in model.bank))
    return Stack((bank, table))


def answer(model: FillTableSpec) -> Answer:
    # Blank values in reading order.
    values = [
        cell.answer for row in model.rows for cell in row if not isinstance(cell, str)
    ]
    return Inline(parse_inline("; ".join(values)))


register(
    tag="fill_table",
    title="Пропуски в таблице",
    model=FillTableSpec,
    body=body,
    answer=answer,
    order=80,
    module=__name__,
)
