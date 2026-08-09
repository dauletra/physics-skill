"""The closing ask: what the lesson leaves the class with.

Separate from `prompt` for the same reason `prompt` is separate from
`objectives`: the fields coincide, the moment in the lesson does not, and it
is the moment the teacher asks for by name.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.text import Style, paragraph
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec

#: What the class reads at the top. These three kinds have no heading field
#: and no kicker on purpose: the word that names the genre *is* the heading,
#: and printing it twice would be printing it twice (docs/pptx.md §7, P4а).
#: It doubles as the kind's name in the generated reference — one word, one
#: place.
HEADING = "Рефлексия"


@spec
class ReflectionSpec:
    """Рефлексия в конце урока."""

    type: Literal["reflection"]
    items: list[str] = field(min_items=1, doc="Вопросы для рефлексии, по строке на вопрос")
    id: Optional[str] = None


def emit(model: ReflectionSpec, scope: str) -> dict[str, object]:
    return {"type": "reflection", "items": [runs(item) for item in model.items]}


def build(model: ReflectionSpec) -> Slide:
    """The genre in the heading, the closing questions under it."""
    layout = layouts.CONTENT
    items = [paragraph(item, Style(bullet=True)) for item in model.items]
    return Slide(
        layout.name,
        layout.places[0].on_slide(2, [paragraph(HEADING)])
        + layout.places[1].on_slide(3, items),
    )


register(
    tag="reflection",
    title=HEADING,
    model=ReflectionSpec,
    emit=emit,
    build=build,
    order=100,
    module=__name__,
)
