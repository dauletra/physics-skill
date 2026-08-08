"""A worked example — the teacher solving at the board while the class follows.

Steps are a list, not one paragraph with line breaks inside: showing them one
at a time is the player's business, and it can only do that if the data says
where a step ends. That is the whole reason this kind exists next to
`content` — the shape of the field carries the meaning, not the styling
(docs/presentation.md §5).
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec


@spec
class ExampleSpec:
    """Разбор задачи у доски: условие, шаги решения, ответ."""

    type: Literal["example"]
    text: str = field(doc="Условие разбираемой задачи")
    steps: list[str] = field(min_items=1, doc="Шаги разбора, по строке на шаг")
    answer: Optional[str] = field(
        default=None, doc="Ответ; когда его показать, решает плеер"
    )
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация к условию")
    id: Optional[str] = None


def emit(model: ExampleSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {
        "type": "example",
        "text": runs(model.text),
        "steps": [runs(step) for step in model.steps],
    }
    if model.visual is not None:
        data["visual"] = emit_visual(model.visual, scope)
    if model.answer is not None:
        data["answer"] = runs(model.answer)
    return data


register(
    tag="example",
    title="Разбор задачи",
    model=ExampleSpec,
    emit=emit,
    order=60,
    module=__name__,
)
