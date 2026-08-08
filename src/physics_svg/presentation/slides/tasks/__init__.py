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

from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec


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


def emit(model: TasksSpec, scope: str) -> dict[str, object]:
    tasks = []
    for index, task in enumerate(model.tasks):
        item: dict[str, object] = {"text": runs(task.text)}
        if task.visual is not None:
            # One scope per picture: ids inside two SVGs on one slide must
            # not collide.
            item["visual"] = emit_visual(task.visual, f"{scope}v{index + 1}")
        if task.answer is not None:
            item["answer"] = runs(task.answer)
        tasks.append(item)
    data: dict[str, object] = {"type": "tasks", "tasks": tasks}
    if model.heading is not None:
        data["heading"] = runs(model.heading)
    return data


register(
    tag="tasks",
    title="Набор задач",
    model=TasksSpec,
    emit=emit,
    order=80,
    module=__name__,
)
