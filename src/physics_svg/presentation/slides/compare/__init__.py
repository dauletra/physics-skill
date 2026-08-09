"""Two or three cases held side by side — equal, parallel, comparable.

The parallel is the meaning, not the layout: a case carries its own name and
its own body, and the player is free to stand them in columns, in rows, or
one under another on a narrow screen. What the schema must not say is
«columns» — that would be layout in the data (principle 10). What it must
say is that these bodies are peers, because that is what a comparison is and
what a list of paragraphs is not.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.presentation.emit import emit_visual, runs
from physics_svg.presentation.pptx import Slide, design, layouts
from physics_svg.presentation.pptx.cell import IDS_PER_CELL, LEAD_LINE, LINE, cell
from physics_svg.presentation.pptx.text import Style, paragraph
from physics_svg.presentation.slides.registry import VISUAL, register
from physics_svg.schema import Invalid, field, spec

#: The genre, for a slide that has no heading of its own to name it.
KICKER = "Сравнение"

#: The name of a case is set a step above its body: it is what the class
#: reads first when the eye moves from one column to the next.
_LABEL = Style(size=design.LEAD, bold=True)

#: What a case keeps for its words when a picture shares the cell: the name
#: and two lines. Measured — at two lines twenty-three specs of the library
#: still read in a cell, at three thirteen (docs/pptx.md §7, P4в).
_CASE_LINES = 2.0


@spec
class CaseSpec:
    """Один случай сопоставления."""

    label: str = field(doc="Название случая: «Равномерное движение»")
    text: Optional[str] = field(default=None, doc="Абзац про этот случай")
    items: Optional[list[str]] = field(default=None, min_items=1, doc="Список признаков")
    visual: Optional[VISUAL] = field(default=None, doc="Иллюстрация случая")

    def check(self) -> None:
        if self.text is None and self.items is None and self.visual is None:
            raise Invalid("случай пуст: нужно хотя бы одно из 'text', 'items', 'visual'")


@spec
class CompareSpec:
    """Слайд сопоставления: два-три случая рядом."""

    type: Literal["compare"]
    cases: list[CaseSpec] = field(
        min_items=2,
        max_items=3,
        doc="Случаи, которые класс держит рядом: два или три",
    )
    heading: Optional[str] = field(default=None, doc="Заголовок: что с чем сравниваем")
    id: Optional[str] = None


def emit(model: CompareSpec, scope: str) -> dict[str, object]:
    cases = []
    for index, case in enumerate(model.cases):
        item: dict[str, object] = {"label": runs(case.label)}
        if case.text is not None:
            item["text"] = runs(case.text)
        if case.items is not None:
            item["items"] = [runs(line) for line in case.items]
        if case.visual is not None:
            # One scope per picture, not per slide: two graphs on one screen
            # would otherwise share ids inside their SVG.
            item["visual"] = emit_visual(case.visual, f"{scope}v{index + 1}")
        cases.append(item)
    data: dict[str, object] = {"type": "compare", "cases": cases}
    if model.heading is not None:
        data["heading"] = runs(model.heading)
    return data


def build(model: CompareSpec) -> Slide:
    """The cases side by side, one cell each.

    Columns, not rows: the frame is divided equally between the cases, and
    equally is what «рядом» means for things the schema calls peers. Three is
    the limit the kind already sets, and the deck agrees with it for its own
    reason — a third of the frame has no room left for a picture (§7, P4в).
    """
    layout = layouts.CELLS_2 if len(model.cases) == 2 else layouts.CELLS_3
    shapes = _head(model.heading, layout)
    for index, (case, box) in enumerate(zip(model.cases, layout.cells)):
        paragraphs = [paragraph(case.label, _LABEL)]
        if case.text is not None:
            paragraphs.append(paragraph(case.text))
        paragraphs.extend(paragraph(item, Style(bullet=True)) for item in case.items or [])
        shapes += cell(
            box,
            paragraphs,
            number=10 + index * IDS_PER_CELL,
            text_height=LEAD_LINE + _CASE_LINES * LINE,
            visual=case.visual,
        )
    return Slide(layout.name, shapes)


def _head(heading: str | None, layout: "layouts.Layout") -> str:
    """The heading if there is one, the genre word if there is not — the
    horizon carries one line."""
    if heading is None:
        return layouts.kicker(KICKER)
    return layout.places[0].on_slide(2, [paragraph(heading)])


register(
    tag="compare",
    title="Сопоставление",
    model=CompareSpec,
    emit=emit,
    build=build,
    order=50,
    module=__name__,
)
