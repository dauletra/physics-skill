"""The layout vocabulary — what a document is made of, before any format.

This is the layer that lets one document reach two outputs. A component or a
question says *what to print* (a paragraph, a list with letters, a table with
gaps, a picture); a backend decides *how it looks* in HTML or in Word. Nobody
below this line writes markup, and nobody above it knows which format is
being produced.

The vocabulary is closed and small on purpose — it is what the document
already prints, written out. A new element is added when a new pedagogical
kind genuinely needs one, never in advance: the same rule `elements/` lives
by. Everything here is a frozen dataclass of tuples, so a layout is
comparable, hashable and safe to build once and emit twice.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Optional, Union

#: Where a run sits relative to the baseline. Authors type `<sup>`/`<sub>`
#: in any text field; `inline.parse_inline` turns those into runs.
Script = Literal["", "sup", "sub"]

#: What a list puts in front of an item.
Marker = Literal["none", "number", "letter"]

#: How a series of items fills the width.
ColumnMode = Literal["single", "two", "inline"]


# --- inline -------------------------------------------------------------


@dataclass(frozen=True)
class Run:
    """A stretch of author text. Raw, unescaped — escaping is a backend's
    job, which is what keeps the same string printable as HTML and as XML."""

    text: str
    script: Script = ""


@dataclass(frozen=True)
class Blank:
    """A ruled space inside a line of text, as wide as the author typed it.

    Carries no answer and never reaches the answers section: it is ruling the
    paper, not asking a question.
    """

    width_ch: int


@dataclass(frozen=True)
class Gap:
    """A gap to be filled in — the one `fill_text` and `fill_table` share."""


@dataclass(frozen=True)
class Slot:
    """A short writing line: «Ответ: ______», the line beside a group name."""

    width_px: int = 150


@dataclass(frozen=True)
class Square:
    """A box to write a number or a letter in — the `rank` control."""


@dataclass(frozen=True)
class Verdict:
    """«☐ Верно ☐ Неверно» — one widget, because the two boxes are one
    choice; a backend prints it whole rather than assembling it again."""


Inline = Union[Run, Blank, Gap, Slot, Square, Verdict]

#: A line's worth of inline content.
Text = tuple[Inline, ...]


# --- blocks -------------------------------------------------------------


@dataclass(frozen=True)
class Para:
    """A paragraph: a problem statement, an explanation, a definition."""

    runs: Text


@dataclass(frozen=True)
class Phrase:
    """Inline content with nothing around it — a line inside a container that
    already provides the framing (an answer beside its number)."""

    runs: Text


@dataclass(frozen=True)
class Line:
    """One line of its own, without a paragraph's spacing: «Ответ: ______»."""

    runs: Text


@dataclass(frozen=True)
class Hint:
    """A small remark to the student — «Отметьте все подходящие варианты»."""

    runs: Text


@dataclass(frozen=True)
class Heading:
    """The name of the sheet (1) or of a section (2). There is no level 3:
    inside a task the hierarchy is drawn by numbers and letters."""

    level: int
    runs: Text


@dataclass(frozen=True)
class Rule:
    """A horizontal line between parts of the document."""


@dataclass(frozen=True)
class Statement:
    """Something to judge on the left, its control on the right — shared by
    `true_false`, `rank` and `classify` so their rows line up."""

    runs: Text
    control: Inline


#: What a list can hold: a line of text, or a statement with its control.
Item = Union[Text, Statement]


@dataclass(frozen=True)
class Bullets:
    """A series of items with an optional marker.

    One visual language for options, statements, ranked items and plain
    bullets, so a document does not sprout four ways of showing a series.
    """

    items: tuple[Item, ...]
    marker: Marker = "none"
    columns: ColumnMode = "single"


@dataclass(frozen=True)
class Lines:
    """A column of short lines — an answer with one line per element."""

    rows: tuple[Text, ...]


@dataclass(frozen=True)
class Grid:
    """A real two-dimensional table with named columns."""

    headers: tuple[Text, ...]
    rows: tuple[tuple[Text, ...], ...]


@dataclass(frozen=True)
class Bank:
    """The things to choose from, printed above the content they belong to —
    a word bank for a gap, the group names for `classify`."""

    label: str
    items: tuple[Text, ...]


@dataclass(frozen=True)
class Picture:
    """An illustration, still as its own model.

    The model is carried, not a drawing: an HTML page wants SVG and a Word
    file wants shapes, and both are built from the same spec by the backend.
    `scope` makes element ids unique on the page it lands on.
    """

    model: Any
    scope: str


@dataclass(frozen=True)
class Spaced:
    """A block standing on its own in the document's flow, with the usual gap
    after it. Containers place themselves; leaves are wrapped in this."""

    block: "Block"


@dataclass(frozen=True)
class Stack:
    """Blocks one after another, with nothing added around them."""

    blocks: tuple["Block", ...]


@dataclass(frozen=True)
class Columns:
    """Blocks side by side. Without an explicit count every child claims a
    column of its own; with one, children wrap filling columns downwards."""

    blocks: tuple["Block", ...]
    columns: Optional[int] = None


@dataclass(frozen=True)
class Facing:
    """Two series read across one another — the columns of `match`. Wider
    apart than a layout row: the eye has to pair them, not compare them."""

    blocks: tuple["Block", ...]


@dataclass(frozen=True)
class Numbered:
    """A task: its number stands beside the whole of it, in a gutter."""

    number: int
    blocks: tuple["Block", ...]


@dataclass(frozen=True)
class Lettered:
    """A subtask: its letter stands beside it, and it is indented from the
    task's shared statement."""

    letter: Optional[str]
    blocks: tuple["Block", ...]


@dataclass(frozen=True)
class AnswerRow:
    """One line of the answers section: the caption («3.», «3. б)»), the
    answer already laid out, and the teacher's explanation."""

    caption: str
    blocks: tuple["Block", ...]
    explanation: Optional[Text] = None


@dataclass(frozen=True)
class Answers:
    """The section at the end. Bodies never contain answers; this is the only
    place one is printed, which is why a handout is this document without a
    section rather than a second rendering of the same bodies."""

    rows: tuple[AnswerRow, ...]


Block = Union[
    Para,
    Phrase,
    Line,
    Hint,
    Heading,
    Rule,
    Bullets,
    Lines,
    Grid,
    Bank,
    Picture,
    Spaced,
    Stack,
    Columns,
    Facing,
    Numbered,
    Lettered,
    Answers,
]

#: A body that prints nothing at all — an `open` question, whose statement and
#: writing space are its neighbours. Not the same as an empty paragraph: no
#: room is taken.
NOTHING = Stack(())


def is_empty(block: Block) -> bool:
    return isinstance(block, Stack) and not block.blocks


def grid_rows(count: int, columns: int) -> int:
    """How many rows `count` items need to fill `columns` top to bottom.

    Filling columns downwards is a promise about which item lands where, so
    the number of rows has to be exact rather than balanced by the backend.
    Both backends ask this function, so both place item 4 in the same place.
    """
    return -(-count // columns)


def column_order(count: int, columns: int) -> list[list[Optional[int]]]:
    """The same promise, read row by row: item indices in the order a backend
    that builds rows has to emit them, `None` for a cell nothing lands in.

    HTML never needs this — the grid fills itself — but the promise is the
    document's, not the format's, so it is stated once here rather than
    reconstructed by whoever lays out a table.
    """
    rows = grid_rows(count, columns)
    return [
        [column * rows + row if column * rows + row < count else None for column in range(columns)]
        for row in range(rows)
    ]
