"""A task for a student at the board.

Deliberately not the document's `open` question: there is no writing
surface, no sheet numbering and no answers section here. The answer, when
given, is for the teacher — when and how to reveal it is the player's
decision, not a field.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.inline import Run, parse_inline
from physics_svg.presentation.pptx import Slide, design, layouts
from physics_svg.presentation.pptx.picture import picture
from physics_svg.presentation.pptx.text import Style, joined_paragraph, paragraph
from physics_svg.presentation.pptx.timing import Reveal
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec

#: What stands before the answer. The word is not decoration: read aloud
#: without it, «12 с» under a task is a number of unclear origin.
ANSWER_LABEL = "Ответ: "


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


def _layout_for(model: BoardTaskSpec) -> "layouts.Layout":
    """Where the picture goes, if there is one — the same measurement the
    explanation slide makes, against a shorter box.

    Shorter because the answer keeps a band at the foot of the frame whether
    it is filled or not: the class always looks for it in one place. That
    band is why the choice matters more here than on an explanation slide —
    there is less height to lose.
    """
    if model.visual is None:
        return layouts.TASK
    assert layouts.TASK_SPLIT.picture is not None
    if layouts.reads_in(layouts.TASK_SPLIT.picture, model.visual):
        return layouts.TASK_SPLIT
    return layouts.TASK_STACK


def build(model: BoardTaskSpec) -> Slide:
    """The statement, the picture, the answer — the player's own order.

    The answer waits for a click. The class gets the task and the picture
    when the slide comes up, and the answer only when the teacher decides —
    which is the whole reason a task is a slide of its own.
    """
    layout = _layout_for(model)
    shapes = layout.places[0].on_slide(2, [paragraph(model.text)])
    if model.visual is not None:
        assert layout.picture is not None
        shapes += picture(model.visual, layout.picture)
    if model.answer is None:
        return Slide(layout.name, shapes)
    shapes += layout.places[1].on_slide(3, [_answer(model.answer)])
    return Slide(layout.name, shapes, reveals=(Reveal(3),))


def _answer(answer: str) -> str:
    """«Ответ: 12 с» — the word auxiliary, the value the point.

    The player set the same line and hung an accent plate over it, because
    there the plate was a button the teacher had to hit with a finger. Here
    nothing is clickable yet, and an accent with nothing to press would say
    «control» about a line of text.
    """
    return joined_paragraph(
        [
            ([Run(ANSWER_LABEL)], Style(colour=design.INK_FAINT)),
            (parse_inline(answer), Style(bold=True)),
        ]
    )


register(
    tag="board_task",
    title="Задача у доски",
    model=BoardTaskSpec,
    build=build,
    order=70,
    module=__name__,
)
