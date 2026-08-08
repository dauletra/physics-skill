"""Two or three cases held side by side — equal, parallel, comparable.

The parallel is the meaning, not the layout: a case carries its own name and
its own body, and the player is free to stand them in columns, in rows, or
one under another on a narrow screen. What the schema must not say is
«columns» — that would be layout in the data (principle 10). What it must
say is that these bodies are peers, because that is what a comparison is and
what a list of paragraphs is not.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import Invalid, field, spec


@spec
class CaseSpec:
    """Один случай сопоставления."""

    label: str = field(doc="Название случая: «Равномерное движение»")
    text: Optional[str] = field(default=None, doc="Абзац про этот случай")
    items: Optional[list[str]] = field(default=None, min_items=1, doc="Список признаков")
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация случая")

    def check(self) -> None:
        if self.text is None and self.items is None and self.visual is None:
            raise Invalid("случай пуст: нужно хотя бы одно из 'text', 'items', 'visual'")


@spec
class CompareSpec:
    """Слайд сопоставления: два-три случая рядом."""

    type: Literal["compare"]
    cases: list[CaseSpec] = field(
        min_items=2,
        max_items=3,
        doc="Случаи, которые класс держит рядом: два или три",
    )
    heading: Optional[str] = field(default=None, doc="Заголовок: что с чем сравниваем")
    id: Optional[str] = None


def emit(model: CompareSpec, scope: str) -> dict[str, object]:
    cases = []
    for index, case in enumerate(model.cases):
        item: dict[str, object] = {"label": runs(case.label)}
        if case.text is not None:
            item["text"] = runs(case.text)
        if case.items is not None:
            item["items"] = [runs(line) for line in case.items]
        if case.visual is not None:
            # One scope per picture, not per slide: two graphs on one screen
            # would otherwise share ids inside their SVG.
            item["visual"] = emit_visual(case.visual, f"{scope}v{index + 1}")
        cases.append(item)
    data: dict[str, object] = {"type": "compare", "cases": cases}
    if model.heading is not None:
        data["heading"] = runs(model.heading)
    return data


register(
    tag="compare",
    title="Сопоставление",
    model=CompareSpec,
    emit=emit,
    order=50,
    module=__name__,
)
