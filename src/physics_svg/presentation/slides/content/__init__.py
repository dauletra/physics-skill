"""Explaining the topic — the workhorse slide of a lesson.

One flexible shape instead of a slide kind per rhetorical device: a heading,
a paragraph, a list, an illustration, in any combination that is not empty.
How they sit on the screen — the illustration beside the text or under it —
is the player's decision, not a field (docs/presentation.md §5).
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.picture import picture
from physics_svg.presentation.pptx.text import Style, paragraph
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import Invalid, field, spec


@spec
class ContentSpec:
    """Слайд объяснения: заголовок, текст, список, иллюстрация."""

    type: Literal["content"]
    heading: Optional[str] = field(default=None, doc="Заголовок слайда")
    text: Optional[str] = field(default=None, doc="Абзац объяснения")
    items: Optional[list[str]] = field(default=None, min_items=1, doc="Список, по строке на пункт")
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация — спека визуала, как в документе")
    id: Optional[str] = None

    def check(self) -> None:
        # A heading alone announces content that never comes — the slide
        # must carry something to explain (principle 8: a node in its
        # minimal valid form does not print emptiness).
        if self.text is None and self.items is None and self.visual is None:
            raise Invalid("слайд пуст: нужно хотя бы одно из 'text', 'items', 'visual'")


def _layout_for(model: ContentSpec) -> "layouts.Layout":
    """Which of the three shapes of this kind the slide takes.

    The player decided this by measuring — it laid the slide out and moved
    the picture out of the text column if it had been squeezed. That much
    measurement survives: the picture is drawn before the slide is, so its
    frame and its smallest label are known, and whether the label will be
    legible beside the text is arithmetic rather than a guess.

    Beside the text, then, only if it reads there. A tall instrument does;
    a wide graph does not — fitted into the column it loses its height, and
    its numbers land under the size a class reads at. Those go above the
    picture instead, with the frame's full width beneath them.
    """
    if model.visual is None:
        return layouts.CONTENT
    if model.text is None and model.items is None:
        return layouts.CONTENT_FIGURE
    assert layouts.CONTENT_SPLIT.picture is not None
    if layouts.reads_in(layouts.CONTENT_SPLIT.picture, model.visual):
        return layouts.CONTENT_SPLIT
    return layouts.CONTENT_STACK


def build(model: ContentSpec) -> Slide:
    """Heading, then whatever explains it.

    A paragraph and a list live in the same place, one after the other: they
    are both the body of the explanation, and giving each its own box would
    make the gap between them a decision nobody took. The list is bulleted,
    the paragraph is not — that is the only difference the layout draws.
    """
    layout = _layout_for(model)
    shapes = ""
    if model.heading is not None:
        shapes += layout.places[0].on_slide(2, [paragraph(model.heading)])
    paragraphs = []
    if model.text is not None:
        paragraphs.append(paragraph(model.text, Style(bullet=False)))
    for item in model.items or []:
        paragraphs.append(paragraph(item, Style(bullet=True)))
    if paragraphs:
        shapes += layout.places[1].on_slide(3, paragraphs)
    if model.visual is not None:
        assert layout.picture is not None
        shapes += picture(model.visual, layout.picture)
    return Slide(layout.name, shapes)


register(
    tag="content",
    title="Объяснение",
    model=ContentSpec,
    build=build,
    order=30,
    module=__name__,
)
