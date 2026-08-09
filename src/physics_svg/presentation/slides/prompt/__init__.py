"""Questions to the class — the frontal ask, a screenful of them.

The same shape as `objectives` and `reflection`, and deliberately a kind of
its own: what the list means decides where it stands in the lesson and how
the player labels it. A slide type is a meaning, not a set of fields.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.text import Style, paragraph
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec

#: What the class reads at the top. These three kinds have no heading field
#: and no kicker on purpose: the word that names the genre *is* the heading,
#: and printing it twice would be printing it twice (docs/pptx.md §7, P4а).
#: It doubles as the kind's name in the generated reference — one word, one
#: place.
HEADING = "Вопросы классу"


@spec
class PromptSpec:
    """Вопросы классу для фронтального опроса."""

    type: Literal["prompt"]
    items: list[str] = field(min_items=1, doc="Вопросы, по строке на вопрос")
    id: Optional[str] = None


def build(model: PromptSpec) -> Slide:
    """The genre in the heading, the questions under it — the same shape
    as `objectives` and `reflection`, because on the screen it *is* the same
    shape. What differs is where in the lesson it stands."""
    layout = layouts.CONTENT
    items = [paragraph(item, Style(bullet=True)) for item in model.items]
    return Slide(
        layout.name,
        layout.places[0].on_slide(2, [paragraph(HEADING)])
        + layout.places[1].on_slide(3, items),
    )


register(
    tag="prompt",
    title=HEADING,
    model=PromptSpec,
    build=build,
    order=90,
    module=__name__,
)
