"""Classification — sort the items into named groups."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Rows
from physics_svg.document.domain import Domain
from physics_svg.document.html import bank_list, blank, list_html, statement_row
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import t
from physics_svg.draw import esc
from physics_svg.schema import field, spec


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


def body(model: ClassifySpec) -> str:
    # The groups are printed, not left to the author to repeat in a
    # neighbouring `text`: they are required data of this question, and a
    # sheet that only lists the items asks the student to guess the groups.
    rows = [statement_row(esc(item.text), blank(115)) for item in model.items]
    return bank_list(model.categories, t("groups_label")) + list_html(rows)


def answer(model: ClassifySpec) -> Answer:
    """A line per group, in the author's order of `categories`.

    An empty group keeps its line with a dash rather than disappearing: a
    distractor the students had to reject is part of what the teacher checks.
    """
    rows = []
    for category in model.categories:
        texts = [item.text for item in model.items if item.category == category]
        rows.append(esc(f"{category}: {', '.join(texts) if texts else '—'}"))
    return Rows(rows)


register(
    tag="classify",
    title="Классификация",
    model=ClassifySpec,
    body=body,
    answer=answer,
    order=60,
    module=__name__,
)
