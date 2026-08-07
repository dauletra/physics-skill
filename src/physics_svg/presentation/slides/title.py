"""The opening slide — the lesson's name, said large."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class TitleSpec:
    """Титульный слайд: тема урока."""

    type: Literal["title"]
    text: str = field(doc="Тема урока")
    subtitle: Optional[str] = field(default=None, doc="Строка под темой: предмет, класс")
    id: Optional[str] = None


register(
    tag="title",
    title="Титульный слайд",
    model=TitleSpec,
    order=10,
    module=__name__,
)
