"""Classification — sort the items into named groups."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Rows
from physics_svg.document.domain import Domain
from physics_svg.document.layout import Bank, Bullets, Item, Slot, Stack, Statement
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import t
from physics_svg.inline import parse_inline
from physics_svg.schema import field, spec

#: The line beside a group name: short, because the answer is one word.
_LINE_PX = 115


@spec
class ClassifyItemSpec:
    """Объект с правильной категорией инлайн."""

    text: str
    category: str


@spec
class ClassifySpec:
    """Распределение объектов по категориям."""

    type: Literal["classify"]
    categories: list[str] = field(min_items=1, doc="Категории; пустая допустима — дистрактор")
    items: list[ClassifyItemSpec] = field(min_items=1)
    id: Optional[str] = None
    explanation: Optional[str] = None

    @property
    def domain(self) -> Domain:
        """The groups: printed above the items, extras allowed as distractors."""
        return Domain(self.categories, field_name="categories")

    def check(self) -> None:
        self.domain.check()
        for i, item in enumerate(self.items):
            self.domain.check_member(item.category, field="items", index=i, attr="category")


def body(model: ClassifySpec) -> Stack:
    # The groups are printed, not left to the author to repeat in a
    # neighbouring `text`: they are required data of this question, and a
    # sheet that only lists the items asks the student to guess the groups.
    rows: tuple[Item, ...] = tuple(
        Statement(parse_inline(item.text), Slot(_LINE_PX)) for item in model.items
    )
    bank = Bank(t("groups_label"), tuple(parse_inline(name) for name in model.categories))
    return Stack((bank, Bullets(rows)))


def answer(model: ClassifySpec) -> Answer:
    """A line per group, in the author's order of `categories`.

    An empty group keeps its line with a dash rather than disappearing: a
    distractor the students had to reject is part of what the teacher checks.
    """
    rows = []
    for category in model.categories:
        texts = [item.text for item in model.items if item.category == category]
        rows.append(parse_inline(f"{category}: {', '.join(texts) if texts else '—'}"))
    return Rows(tuple(rows))


register(
    tag="classify",
    title="Классификация",
    model=ClassifySpec,
    body=body,
    answer=answer,
    order=60,
    module=__name__,
)
