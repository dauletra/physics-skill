"""One equal piece of a slide: a case of a comparison, a task of a set.

Two kinds of slide put several peers on the screen at once, and the class has
to see where one ends and the next begins. The player did it with a rule
along the top of each piece, and the reason it is a rule and not a fill is
worth carrying over: a cell often holds an illustration, whose grid is drawn
in service grey, and a tinted panel takes what little contrast that grey has
([slide-design.md](../../../../docs/slide-design.md) §6.4).

**A cell is drawn, not placed.** Everywhere else on a slide the layout
declares a place and the slide fills it, which is what makes «Сброс слайда»
work. A cell cannot be that: how many pieces there are, whether each carries
a picture and whether each carries an answer are the author's, and a
placeholder for every combination is a layout for every combination. So the
layout declares the grid — where the pieces sit — and the piece itself is
shapes. The heading above them stays a place, because that is the text an
outline view has to see.

**The split inside a cell is fixed, and that is a decision with a number.**
The player let the text take what it needed and gave the picture the rest;
that needs a measurement at show time, which a deck has no way to make. So a
cell with a picture reserves two lines for its text and gives the picture the
rest — measured: at two lines twenty-three specs of the library are still
legible in the cell, at three only thirteen. What a cell holds is therefore
a limit, and it is written down for the model in the `doc.md` of both kinds.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from physics_svg.ooxml import el
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.picture import picture
from physics_svg.presentation.pptx.shape import plain_shape
from physics_svg.presentation.pptx.text import text_body

#: The player's spacing unit, which the cell is built out of: the rule on top,
#: the air under it, the air between the parts.
STEP = design.cqh(1.5)
RULE_HEIGHT = 0.3 * STEP
PAD = STEP
GAP = STEP

#: One line of body text and one of a statement, including leading.
LINE = design.TEXT * design.LEADING
LEAD_LINE = design.LEAD * design.LEADING

#: The band an answer keeps at the foot of a cell. It is reserved for every
#: cell of the slide as soon as one of them has an answer: a row of answers at
#: different heights reads as broken typesetting rather than as a row.
ANSWER_HEIGHT = design.TEXT * design.LEADING * 1.2

#: A picture is never squeezed below this. Half the floor a picture gets when
#: it has the slide to itself — the full one would push a set of four tasks
#: out of the frame (docs/slide-design.md §6.4).
PICTURE_MIN = design.VISUAL_MIN / 2

#: How many shape ids one cell may use. The picture inside it takes a range
#: of its own, so this counts only the cell's own shapes.
IDS_PER_CELL = 8


def cell(
    box: tuple[float, float, float, float],
    paragraphs: Sequence[str],
    *,
    number: int,
    text_height: Optional[float] = None,
    visual: Any = None,
    answer: Sequence[str] = (),
    reserve_answer: bool = False,
) -> str:
    """One cell of a grid, as shapes.

    `text_height` is what the text is given when a picture shares the cell
    with it; without a picture the text has the whole cell and the argument
    is ignored. `reserve_answer` keeps the band at the foot even when this
    particular cell has nothing to put in it.
    """
    x, y, width, height = box
    top = y + RULE_HEIGHT + PAD
    bottom = y + height - (ANSWER_HEIGHT + GAP if reserve_answer else 0.0)
    shapes = _rule(x, y, width, number)

    picture_top = bottom
    if visual is not None:
        room = bottom - top
        wanted = room - (text_height or 0.0) - GAP
        # The floor wins over the text, but never takes its last line: a
        # picture with no statement above it is a task nobody can read.
        picture_height = max(PICTURE_MIN, wanted)
        picture_height = min(picture_height, room - LINE - GAP)
        picture_top = bottom - picture_height
        shapes += picture(
            visual, (x, picture_top, width, picture_height), first_id=number * 1000
        )

    if paragraphs:
        text_bottom = picture_top - GAP if visual is not None else bottom
        shapes += plain_shape(
            number + 1, "Текст", (x, top, width, text_bottom - top), text_body(paragraphs)
        )
    if answer:
        shapes += plain_shape(
            number + 2,
            "Ответ",
            (x, y + height - ANSWER_HEIGHT, width, ANSWER_HEIGHT),
            text_body(answer, anchor="b"),
        )
    return shapes


def _rule(x: float, y: float, width: float, number: int) -> str:
    """The accent line that says where a cell begins."""
    return plain_shape(
        number,
        "Линейка ячейки",
        (x, y, width, RULE_HEIGHT),
        fill=el("a:solidFill", children=el("a:srgbClr", {"val": design.ACCENT})),
    )


def text_only_height(box: tuple[float, float, float, float], *, answer: bool) -> float:
    """How much room a cell gives text when nothing else shares it — the
    number both kinds report as their capacity."""
    return box[3] - RULE_HEIGHT - PAD - (ANSWER_HEIGHT + GAP if answer else 0.0)
