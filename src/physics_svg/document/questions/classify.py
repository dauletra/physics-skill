"""Classification — sort the items into named groups."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.html import blank, list_html, statement_row
from physics_svg.document.questions.registry import register
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec


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

    def check(self) -> None:
        if len(set(self.categories)) != len(self.categories):
            raise Invalid(
                f"категории должны быть уникальны, получено {self.categories}", field="categories"
            )
        for i, item in enumerate(self.items):
            if item.category not in self.categories:
                raise Invalid(
                    f"items[{i}].category = '{item.category}' нет среди categories "
                    f"{self.categories}",
                    field="items",
                )


def body(model: ClassifySpec) -> str:
    rows = [statement_row(esc(item.text), blank(115)) for item in model.items]
    return list_html(rows)


def answer(model: ClassifySpec) -> str:
    # Grouped in the author's order of `categories`; an empty group is shown
    # with a dash rather than omitted, so a distractor stays visible.
    groups = []
    for category in model.categories:
        texts = [item.text for item in model.items if item.category == category]
        groups.append(f"{category}: {', '.join(texts) if texts else '—'}")
    return esc("; ".join(groups))


register(
    tag="classify", title="Классификация", model=ClassifySpec, body=body, answer=answer,
    module=__name__,
)
