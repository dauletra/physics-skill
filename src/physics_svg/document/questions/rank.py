"""Ordering — put the items in the right sequence."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.html import list_html, statement_row
from physics_svg.document.questions.registry import register
from physics_svg.draw import esc
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


def body(model: RankSpec) -> str:
    rows = [
        statement_row(esc(item.text), '<span class="rank-square"></span>')
        for item in model.items
    ]
    return list_html(rows)


def answer(model: RankSpec) -> str:
    # Item numbers, as shown, in the correct order.
    order = sorted(range(len(model.items)), key=lambda i: model.items[i].position)
    return esc(", ".join(str(i + 1) for i in order))


register(
    tag="rank", title="Упорядочивание", model=RankSpec, body=body, answer=answer, module=__name__
)
