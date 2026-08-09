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
"""

from __future__ import annotations

from dataclasses import dataclass


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

    @property
    def steps(self) -> tuple[float, ...]:
        """The scale, ascending — what a test can walk over."""
        return (self.micro, self.label, self.caption, self.number, self.axis, self.display)


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
)
