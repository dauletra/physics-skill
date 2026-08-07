"""The lesson's objectives — what the class will be able to do after it."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class ObjectivesSpec:
    """Цели урока."""

    type: Literal["objectives"]
    items: list[str] = field(min_items=1, doc="Цели, по строке на каждую")
    id: Optional[str] = None


register(
    tag="objectives",
    title="Цели урока",
    model=ObjectivesSpec,
    order=20,
    module=__name__,
)
