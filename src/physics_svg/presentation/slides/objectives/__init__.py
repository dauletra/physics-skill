"""The lesson's objectives — what the class will be able to do after it."""

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
HEADING = "Цели урока"


@spec
class ObjectivesSpec:
    """Цели урока."""

    type: Literal["objectives"]
    items: list[str] = field(min_items=1, doc="Цели, по строке на каждую")
    id: Optional[str] = None


def emit(model: ObjectivesSpec, scope: str) -> dict[str, object]:
    return {"type": "objectives", "items": [runs(item) for item in model.items]}


def build(model: ObjectivesSpec) -> Slide:
    """The genre in the heading, the objectives under it.

    Nothing here is the kind's own layout: a heading over a list is the
    explanation layout, and using it is what makes an objectives slide look
    like the lesson it opens rather than like a form.
    """
    layout = layouts.CONTENT
    items = [paragraph(item, Style(bullet=True)) for item in model.items]
    return Slide(
        layout.name,
        layout.places[0].on_slide(2, [paragraph(HEADING)])
        + layout.places[1].on_slide(3, items),
    )


register(
    tag="objectives",
    title=HEADING,
    model=ObjectivesSpec,
    emit=emit,
    build=build,
    order=20,
    module=__name__,
)
