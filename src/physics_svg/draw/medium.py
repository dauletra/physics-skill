"""How far away the picture will be read from — the scale its labels sit on.

The library is drawn once and shown twice: on an A4 sheet held at arm's
length, and on a classroom board seven metres away. The drawing is the same
in both places — the same divisions, the same values, the same thing a
student can read off it. What cannot be the same is how large the writing
is, because a label is a fixed fraction of the picture, and the picture is
fitted into whatever room the destination gives it.

So a medium is not a theme and not an author's choice: it is the destination
saying how it will show the result. `document` and Word ask for the sheet,
the presentation asks for the board, and nothing in a spec mentions either.

**Six steps, and every label stands on one of them.** They are not invented
here — they are the sizes the library already used, given names:

    micro    the second scale of a multi-range meter, gram weights, a vernier
    label    the numbers of an instrument scale, the unit beside it
    caption  the line under a picture, the unit on a dial
    number   the numbers of a graph axis, a vector's name, a legend
    axis     the quantity a graph axis measures
    display  a digital readout

A renderer picks the step by what the label *is*, never by how it should
look; a step that no role needs is a step that should not exist. See
docs/visual-scale.md for where the numbers come from and what the board
scale has to clear.

**And a second ladder, of service grey.** A gridline, a ruled square, a
construction line — none of them are the drawing, all of them are there to be
read *under* it, and how weak «weak» may be is the destination's business
too. On paper it is a photocopy and a pencil; on a lit panel the faintest of
them stops existing (§3.7). Four rungs, the same four the library already
drew with, named by the job rather than by the shade.
"""

from __future__ import annotations

from dataclasses import dataclass

from physics_svg.draw.style import (
    GREY,
    GREY_BOARD,
    GREY_FAINT,
    GREY_FAINT_BOARD,
    GREY_LIGHT,
    GREY_LIGHT_BOARD,
    GREY_STRONG,
    GREY_STRONG_BOARD,
)


@dataclass(frozen=True)
class Medium:
    """The label scale of one destination, in user units."""

    #: Identifies the medium in error messages and in file names.
    name: str
    micro: float
    label: float
    caption: float
    number: float
    axis: float
    display: float

    #: The border of a ruled field, the centimetre line of graph paper.
    rule: str
    #: The ruling itself: an exercise-book square, a dot, a construction line.
    ruling: str
    #: A chart's grid at a numbered division.
    grid: str
    #: A sub-division inside one step: the millimetre, the fifth of a cell.
    grid_fine: str

    @property
    def steps(self) -> tuple[float, ...]:
        """The scale, ascending — what a test can walk over."""
        return (self.micro, self.label, self.caption, self.number, self.axis, self.display)

    @property
    def greys(self) -> tuple[str, ...]:
        """The service ladder, strongest first — what a test can walk over."""
        return (self.rule, self.ruling, self.grid, self.grid_fine)


#: A4 in the hand. These are the sizes the library has always drawn at, and
#: they are fixed: a bigger label on paper takes room away from the picture,
#: and the picture gets printed and photocopied.
SHEET = Medium(
    name="sheet",
    micro=6.0,
    label=7.0,
    caption=8.0,
    number=9.0,
    axis=10.0,
    display=15.0,
    rule=GREY_STRONG,
    ruling=GREY,
    grid=GREY_LIGHT,
    grid_fine=GREY_FAINT,
)

#: A classroom board, seven metres away. Every step is half again as large,
#: which is not a taste but a measurement: at ×1,5 the smallest label of
#: every picture in the library reaches the threshold the class reads at,
#: fitted into the narrower of the two places a slide gives it
#: (docs/visual-scale.md §6.1).
#:
#: The display is the exception at ×1,27: it is the largest thing on an
#: instrument already, and its job is to be read as a number rather than to
#: compete with the scale beside it.
BOARD = Medium(
    name="board",
    micro=9.0,
    label=10.5,
    caption=12.0,
    number=13.5,
    axis=15.0,
    display=19.0,
    rule=GREY_STRONG_BOARD,
    ruling=GREY_BOARD,
    grid=GREY_LIGHT_BOARD,
    grid_fine=GREY_FAINT_BOARD,
)
