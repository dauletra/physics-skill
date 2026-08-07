"""Ordering — put the items in the right sequence."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Rows
from physics_svg.document.layout import Bullets, Item, Square, Statement
from physics_svg.document.questions.registry import register
from physics_svg.inline import parse_inline
from physics_svg.schema import Invalid, field, spec


@spec
class RankItemSpec:
    """Пункт с правильной позицией инлайн."""

    text: str
    position: int = field(doc="Правильное место пункта, от 1")


@spec
class RankSpec:
    """Расстановка в правильном порядке."""

    type: Literal["rank"]
    items: list[RankItemSpec] = field(
        min_items=1, doc="Порядок массива — порядок показа (перемешанный)"
    )
    id: Optional[str] = None
    explanation: Optional[str] = None

    def check(self) -> None:
        positions = sorted(item.position for item in self.items)
        if positions != list(range(1, len(self.items) + 1)):
            raise Invalid(
                f"позиции должны быть перестановкой 1..{len(self.items)}, получено {positions}",
                field="items",
            )


def body(model: RankSpec) -> Bullets:
    rows: tuple[Item, ...] = tuple(
        Statement(parse_inline(item.text), Square()) for item in model.items
    )
    return Bullets(rows)


def answer(model: RankSpec) -> Answer:
    """Position and item, one line each, in the correct order.

    Not the item numbers alone (`2, 3, 1`): the items carry no printed
    numbers, so counting rows is the only way to read such a line — and it
    reads just as well as "item 1 goes second", which is a different and
    wrong answer. A line per position cannot be misread.
    """
    ordered = sorted(model.items, key=lambda item: item.position)
    return Rows(tuple(parse_inline(f"{item.position} — {item.text}") for item in ordered))


register(
    tag="rank",
    title="Упорядочивание",
    model=RankSpec,
    body=body,
    answer=answer,
    order=50,
    module=__name__,
)
