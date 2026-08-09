"""A stage divider — the lesson's punctuation.

A slide, not a container: the top of a presentation is a flat list, and a
stage that swallowed its slides would be a layout that changes meaning
(docs/presentation.md §3, principle 8). The data only marks where a stage
begins; building navigation out of those markers is the player's affair.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.text import paragraph
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class SectionSpec:
    """Разделитель этапов урока."""

    type: Literal["section"]
    text: str = field(doc="Название этапа урока")
    id: Optional[str] = None


def build(model: SectionSpec) -> Slide:
    """The stage's name, alone on a dark slide."""
    place = layouts.SECTION.places[0]
    return Slide("section", place.on_slide(2, [paragraph(model.text)]))


register(
    tag="section",
    title="Разделитель этапа",
    model=SectionSpec,
    build=build,
    order=110,
    module=__name__,
)
