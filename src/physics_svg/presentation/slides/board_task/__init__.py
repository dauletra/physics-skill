"""A task for a student at the board.

Deliberately not the document's `open` question: there is no writing
surface, no sheet numbering and no answers section here. The answer, when
given, is for the teacher — when and how to reveal it is the player's
decision, not a field.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec


@spec
class BoardTaskSpec:
    """Задача для решения у доски."""

    type: Literal["board_task"]
    text: str = field(doc="Условие задачи")
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация к условию")
    answer: Optional[str] = field(
        default=None, doc="Ответ для учителя; когда его показать, решает плеер"
    )
    id: Optional[str] = None


def emit(model: BoardTaskSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {"type": "board_task", "text": runs(model.text)}
    if model.visual is not None:
        data["visual"] = emit_visual(model.visual, scope)
    if model.answer is not None:
        data["answer"] = runs(model.answer)
    return data


register(
    tag="board_task",
    title="Задача у доски",
    model=BoardTaskSpec,
    emit=emit,
    order=50,
    module=__name__,
)
