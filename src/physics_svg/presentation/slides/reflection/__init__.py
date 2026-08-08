"""The closing ask: what the lesson leaves the class with.

Separate from `prompt` for the same reason `prompt` is separate from
`objectives`: the fields coincide, the moment in the lesson does not, and it
is the moment the teacher asks for by name.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class ReflectionSpec:
    """Рефлексия в конце урока."""

    type: Literal["reflection"]
    items: list[str] = field(min_items=1, doc="Вопросы для рефлексии, по строке на вопрос")
    id: Optional[str] = None


def emit(model: ReflectionSpec, scope: str) -> dict[str, object]:
    return {"type": "reflection", "items": [runs(item) for item in model.items]}


register(
    tag="reflection",
    title="Рефлексия",
    model=ReflectionSpec,
    emit=emit,
    order=100,
    module=__name__,
)
