"""The presentation manifest — `presentation.json`.

The name of the lesson and the order of the slides, and nothing else:
`title` becomes the deck's document title, what PowerPoint shows in its
window and in a file listing. The slides themselves live one per file in
`slides/<id>.json`, so a targeted edit — «переделай третий слайд» — touches
one small file instead of the whole lesson.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from physics_svg.presentation.slides.registry import slide_annotation
from physics_svg.schema import Deferred, Invalid, field, parse, spec

if TYPE_CHECKING:  # mypy reads this as plain `Any`; at runtime it resolves
    SLIDE = Any
else:
    SLIDE = Deferred(slide_annotation)


@spec
class PresentationSpec:
    """Манифест презентации."""

    title: str = field(
        default="",
        doc="Название урока: уходит в свойства файла презентации",
    )
    order: Optional[list[str]] = field(
        default=None, doc="Порядок слайдов: имена файлов из slides/ без расширения"
    )

    def check(self) -> None:
        if self.order is not None and len(set(self.order)) != len(self.order):
            duplicated = sorted({name for name in self.order if self.order.count(name) > 1})
            raise Invalid(f"в 'order' повторяются слайды: {duplicated}", field="order")


def parse_presentation(data: object, name: str = "presentation.json") -> PresentationSpec:
    return parse(PresentationSpec, data, name=name)


def parse_slide(data: object, name: str = "") -> Any:
    """Validate one slide — the content of one `slides/*.json`."""
    return parse(SLIDE, data, name=name)
