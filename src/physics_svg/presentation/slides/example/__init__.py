"""A worked example — the teacher solving at the board while the class follows.

Steps are a list, not one paragraph with line breaks inside: showing them one
at a time is the player's business, and it can only do that if the data says
where a step ends. That is the whole reason this kind exists next to
`content` — the shape of the field carries the meaning, not the styling
(docs/presentation.md §5).
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.inline import Run, parse_inline
from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.pptx import Slide, design, layouts
from physics_svg.presentation.pptx.picture import picture
from physics_svg.presentation.pptx.text import Style, joined_paragraph, paragraph
from physics_svg.presentation.pptx.timing import Reveal
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import field, spec

#: What stands before the answer, as on a task slide — the deck says «Ответ»
#: the same way wherever an answer appears.
ANSWER_LABEL = "Ответ: "


@spec
class ExampleSpec:
    """Разбор задачи у доски: условие, шаги решения, ответ."""

    type: Literal["example"]
    text: str = field(doc="Условие разбираемой задачи")
    steps: list[str] = field(min_items=1, doc="Шаги разбора, по строке на шаг")
    answer: Optional[str] = field(
        default=None, doc="Ответ; когда его показать, решает плеер"
    )
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация к условию")
    id: Optional[str] = None


def emit(model: ExampleSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {
        "type": "example",
        "text": runs(model.text),
        "steps": [runs(step) for step in model.steps],
    }
    if model.visual is not None:
        data["visual"] = emit_visual(model.visual, scope)
    if model.answer is not None:
        data["answer"] = runs(model.answer)
    return data


def build(model: ExampleSpec) -> Slide:
    """The statement, the steps numbered under it, the answer at the foot.

    The steps come one click at a time and the answer last, so the class
    follows the reasoning instead of reading the end of it. That order is not
    a preference: PowerPoint has one queue of clicks and no way past it, so
    an answer anywhere but last could be opened by a teacher who only meant
    to show the next step (docs/pptx.md §6.2).

    PowerPoint numbers the steps itself rather than the numbers being drawn
    into the text: a teacher who inserts a step gets the rest renumbered
    instead of a list that lies.
    """
    layout = layouts.EXAMPLE_SPLIT if model.visual is not None else layouts.EXAMPLE
    notes: list[str] = []
    shapes = layout.places[0].on_slide(2, [paragraph(model.text, notes=notes)])
    shapes += layout.places[1].on_slide(
        3, [paragraph(step, Style(numbered=True), notes) for step in model.steps]
    )
    if model.visual is not None:
        assert layout.picture is not None
        shapes += picture(model.visual, layout.picture)
    reveals = [Reveal(3, tuple(range(len(model.steps))))]
    if model.answer is not None:
        shapes += layout.places[2].on_slide(4, [_answer(model.answer, notes)])
        reveals.append(Reveal(4))
    return Slide(layout.name, shapes, tuple(notes), tuple(reveals))


def _answer(answer: str, notes: list[str]) -> str:
    """«Ответ: 25 м» — the word auxiliary, the value the point. The same line
    a task at the board carries, because it is the same thing."""
    return joined_paragraph(
        [
            ([Run(ANSWER_LABEL)], Style(colour=design.INK_FAINT)),
            (parse_inline(answer), Style(bold=True)),
        ],
        notes=notes,
    )


register(
    tag="example",
    title="Разбор задачи",
    model=ExampleSpec,
    emit=emit,
    build=build,
    order=60,
    module=__name__,
)
