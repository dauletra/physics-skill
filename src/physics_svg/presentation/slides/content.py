"""Explaining the topic — the workhorse slide of a lesson.

One flexible shape instead of a slide kind per rhetorical device: a heading,
a paragraph, a list, an illustration, in any combination that is not empty.
How they sit on the screen — the illustration beside the text or under it —
is the player's decision, not a field (docs/presentation.md §5).
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import emit_visual, runs
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


def emit(model: ContentSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {"type": "content"}
    if model.heading is not None:
        data["heading"] = runs(model.heading)
    if model.text is not None:
        data["text"] = runs(model.text)
    if model.items is not None:
        data["items"] = [runs(item) for item in model.items]
    if model.visual is not None:
        data["visual"] = emit_visual(model.visual, scope)
    return data


register(
    tag="content",
    title="Объяснение",
    model=ContentSpec,
    emit=emit,
    order=30,
    module=__name__,
)
