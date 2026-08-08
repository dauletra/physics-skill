"""A stage divider — the lesson's punctuation.

A slide, not a container: the top of a presentation is a flat list, and a
stage that swallowed its slides would be a layout that changes meaning
(docs/presentation.md §3, principle 8). The data only marks where a stage
begins; building navigation out of those markers is the player's affair.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import runs
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class SectionSpec:
    """Разделитель этапов урока."""

    type: Literal["section"]
    text: str = field(doc="Название этапа урока")
    id: Optional[str] = None


def emit(model: SectionSpec, scope: str) -> dict[str, object]:
    return {"type": "section", "text": runs(model.text)}


register(
    tag="section",
    title="Разделитель этапа",
    model=SectionSpec,
    emit=emit,
    order=80,
    module=__name__,
)
