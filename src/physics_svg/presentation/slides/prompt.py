"""Questions to the class — the frontal ask, a screenful of them.

The same shape as `objectives` and `reflection`, and deliberately a kind of
its own: what the list means decides where it stands in the lesson and how
the player labels it. A slide type is a meaning, not a set of fields.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class PromptSpec:
    """Вопросы классу для фронтального опроса."""

    type: Literal["prompt"]
    items: list[str] = field(min_items=1, doc="Вопросы, по строке на вопрос")
    id: Optional[str] = None


def emit(model: PromptSpec, scope: str) -> dict[str, object]:
    return {"type": "prompt", "items": [runs(item) for item in model.items]}


register(
    tag="prompt",
    title="Вопросы классу",
    model=PromptSpec,
    emit=emit,
    order=60,
    module=__name__,
)
