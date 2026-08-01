"""What a question hands to the answers section.

A kind returns the *shape* of its answer, not finished layout: one short line,
a line per element, or a block. The section decides how that becomes markup,
which is what keeps every answer on the sheet looking like every other one —
and what stops `plot` from being an exception, where a whole drawing used to
be squeezed into a field meant for «б».

`None` means the question has no answer at all: an `open` question asked
aloud. It is not an empty `Inline` — nothing is printed, not an empty line.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Inline:
    """One short line: a letter, «1-а, 2-б», a number with its unit."""

    html: str


@dataclass(frozen=True)
class Rows:
    """A short answer per element, one line each — ranked items, groups.

    Not a single line joined by semicolons: the teacher reads it against the
    student's sheet element by element.
    """

    rows: list[str]


@dataclass(frozen=True)
class Block:
    """A drawing — the correct graph on the question's own axes."""

    html: str


Answer = Union[Inline, Rows, Block]

#: The compact answer, or nothing at all.
MaybeAnswer = Optional[Answer]
