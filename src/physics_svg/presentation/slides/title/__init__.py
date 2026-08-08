"""The opening slide — the lesson's name, said large."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
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


register(
    tag="title",
    title="Титульный слайд",
    model=TitleSpec,
    emit=emit,
    order=10,
    module=__name__,
)
