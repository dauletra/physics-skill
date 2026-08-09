"""Several tasks on one screen — for rows, variants, or a quick round.

Not a list inside `content`: each task carries its own answer and may carry
its own picture, and the player opens those answers one at a time. A list of
strings cannot say that, which is exactly the test a new kind has to pass
(docs/slide-templates.md §2). One task is `board_task` — at the board the
class solves one at a time, and a set of one is a set only on paper.

Numbering lives in the player, not here: the number of a task is its place
in the list, as it is on a sheet (principle 2).
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.inline import Run, parse_inline
from physics_svg.presentation.pptx import Slide, design, layouts
from physics_svg.presentation.pptx.cell import IDS_PER_CELL, LINE, cell
from physics_svg.presentation.pptx.text import Style, joined_paragraph, paragraph
from physics_svg.presentation.pptx.timing import Reveal
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec

#: The genre, for a slide that has no heading of its own to name it.
KICKER = "Задачи"

#: A task numbers itself by where it stands, exactly as on a sheet. The number
#: is what the teacher says out loud — «решаем вторую» — so it is set in the
#: accent rather than in the faintest grey on the slide.
_NUMBER = Style(bold=True, colour=design.ACCENT)

#: How much of a cell the statement keeps when a picture shares it with it.
#: Two lines, and the number is measured: at two, twenty-three specs of the
#: library still read in the cell; at three, thirteen (docs/pptx.md §7, P4в).
_STATEMENT_LINES = 2.0


@spec
class TaskItemSpec:
    """Одна задача из набора."""

    text: str = field(doc="Условие задачи")
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация к условию")
    answer: Optional[str] = field(default=None, doc="Ответ; открывается щелчком по своей плашке")


@spec
class TasksSpec:
    """Слайд с несколькими задачами: класс видит их сразу все."""

    type: Literal["tasks"]
    tasks: list[TaskItemSpec] = field(
        min_items=2,
        max_items=4,
        doc="Задачи: от двух до четырёх; одна задача — это 'board_task'",
    )
    heading: Optional[str] = field(default=None, doc="Заголовок: «Решите в парах»")
    id: Optional[str] = None


def build(model: TasksSpec) -> Slide:
    """A grid of tasks, one cell each.

    Two stand side by side; three or four fold into two rows, because a column
    narrower than half the frame is not read from the back row — the player's
    rule, and the reason it thinned instead of adding columns.

    The answer band is reserved for every cell as soon as one task has an
    answer: a row of answers at different heights reads as broken typesetting
    rather than as a row.

    The answers wait for a click, and they open **in order** — first task
    first. The player let the teacher open the one the class had got to;
    PowerPoint has one queue and no way to pick out of it, so a set whose
    tasks are solved out of order is a set to give without answers on the
    screen (docs/pptx.md §4).
    """
    layout = _layout_for(model)
    answers = any(task.answer is not None for task in model.tasks)
    shapes = _head(model.heading, layout)
    reveals = []
    for index, (task, box) in enumerate(zip(model.tasks, layout.cells)):
        number = 10 + index * IDS_PER_CELL
        if task.answer:
            reveals.append(Reveal(number + 2))
        shapes += cell(
            box,
            [_statement(index, task.text)],
            number=number,
            text_height=_STATEMENT_LINES * LINE,
            visual=task.visual,
            answer=[paragraph(task.answer, Style(bold=True))] if task.answer else (),
            reserve_answer=answers,
        )
    return Slide(layout.name, shapes, reveals=tuple(reveals))


def _layout_for(model: TasksSpec) -> "layouts.Layout":
    if len(model.tasks) == 2:
        return layouts.CELLS_2
    return layouts.CELLS_3_SQUARE if len(model.tasks) == 3 else layouts.CELLS_4


def _head(heading: str | None, layout: "layouts.Layout") -> str:
    """The heading if there is one, the genre word if there is not.

    The horizon carries one line. A heading already says what this slide is —
    «Решите в парах» is not going to be mistaken for an explanation — so
    printing «Задачи» above it would be the same statement twice.
    """
    if heading is None:
        return layouts.kicker(KICKER)
    return layout.places[0].on_slide(2, [paragraph(heading)])


def _statement(index: int, text: str) -> str:
    """«2. Поезд длиной 240 м…» — the number drawn, not stored.

    Where a task stands is not a property of the task, so the data does not
    carry it, exactly as on a sheet (principle 2).
    """
    return joined_paragraph(
        [([Run(f"{index + 1}. ")], _NUMBER), (parse_inline(text), Style())]
    )


register(
    tag="tasks",
    title="Набор задач",
    model=TasksSpec,
    build=build,
    order=80,
    module=__name__,
)
