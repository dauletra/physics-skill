"""The opening slide — the lesson's name, said large."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.text import paragraph
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class TitleSpec:
    """Титульный слайд: тема урока."""

    type: Literal["title"]
    text: str = field(doc="Тема урока")
    subtitle: Optional[str] = field(default=None, doc="Строка под темой: предмет, класс")
    id: Optional[str] = None


def emit(model: TitleSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {"type": "title", "text": runs(model.text)}
    if model.subtitle is not None:
        data["subtitle"] = runs(model.subtitle)
    return data


def build(model: TitleSpec) -> Slide:
    """The lesson's name on the title layout.

    Both places are filled even when the author gave no subtitle: an empty
    placeholder is what PowerPoint hides, and a missing one is what it shows
    a prompt in the middle of the lesson for.
    """
    places = layouts.TITLE.places
    shapes = places[0].on_slide(2, [paragraph(model.text)])
    if model.subtitle is not None:
        shapes += places[1].on_slide(3, [paragraph(model.subtitle)])
    return Slide("title", shapes)


register(
    tag="title",
    title="Титульный слайд",
    model=TitleSpec,
    emit=emit,
    build=build,
    order=10,
    module=__name__,
)
