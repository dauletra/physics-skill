"""Layout -> WordprocessingML.

**HTML nests, Word is flat.** A task contains a subtask contains a row
contains a block — on screen that is four nested elements; in a Word document
the body is one sequence of `w:p` and `w:tbl` with no nesting at all. So
everything the stylesheet expresses by containment has to become a property
of a paragraph: the gutter of a task number is a hanging indent, the offset
of a subtask is a left indent, the gap after a block is spacing on its last
paragraph.

That last one is why this module builds `Par`/`Tbl` objects first and
serialises them at the end. A container cannot wrap what it contains; it has
to reach into what its children produced and adjust them — set the spacing of
the last paragraph, put the number into the first one, shift them all right.
With finished XML strings none of that is possible.

Two things stay exactly as they are in HTML, because they are decisions of
the document and not of a format: what is numbered (`render.py` already
decided) and that a body never contains an answer.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Optional, Union

from physics_svg.document.emit.docx import styles as st
from physics_svg.document.emit.docx.drawing import Ids, drawing
from physics_svg.document.emit.docx.wml import cell, para, row, run, tab_run, table
from physics_svg.document.layout import (
    Answers,
    Bank,
    Blank,
    Block,
    Bullets,
    Columns,
    Facing,
    Gap,
    Grid,
    Heading,
    Hint,
    Inline,
    Item,
    Lettered,
    Line,
    Lines,
    Math,
    Numbered,
    Para,
    Phrase,
    Picture,
    Rule,
    Run,
    Slot,
    Spaced,
    Square,
    Stack,
    Statement,
    Text,
    Verdict,
    column_order,
)
from physics_svg.document.strings import LETTERS, t
from physics_svg.draw import Unsupported as DrawUnsupported
from physics_svg.ooxml.omml import convert


class Unsupported(ValueError):
    """Something the Word backend cannot print.

    Raised rather than silently skipped: an empty frame on a printed sheet
    gives a teacher no way of telling that it was ever meant to hold a graph.
    """


#: Width of one non-breaking space and of one `ch` at the body size, in CSS
#: pixels. Blanks are ruled with non-breaking spaces, and the stylesheet
#: measures them in `ch` and in `px` — this is the bridge.
_NBSP_PX = st.NBSP_PX
_CH_PX = 8.0

#: `.fill-blank { min-width: 68px }` — a gap in a sentence or a table cell.
_GAP_PX = 68


@dataclass
class Par:
    """One paragraph, still adjustable by the containers around it."""

    runs: str
    style: str = st.NORMAL
    indent: int = 0
    hanging: int = 0
    before: int = 0
    after: int = 0
    right_tab: Optional[int] = None
    border_bottom: bool = False


@dataclass
class Tbl:
    """One table. Cells are already serialised: their content is finished by
    the time a table exists, because a cell starts a fresh flow of its own."""

    rows: list[list[str]]
    widths: list[int]
    borders: bool = False
    header: bool = False
    indent: int = 0
    before: int = 0
    after: int = 0
    cell_margin: int = 0


Node = Union[Par, Tbl]


class Notes:
    """What the build has to tell the teacher about the file it just made.

    Not an error and not a silence: a formula Word could not be given is
    printed as the author typed it, and this is where the fact is written
    down so that the CLI can say it out loud.
    """

    def __init__(self) -> None:
        self._items: list[str] = []

    def add(self, text: str) -> None:
        self._items.append(text)

    @property
    def items(self) -> tuple[str, ...]:
        return tuple(self._items)


@dataclass(frozen=True)
class Frame:
    """What the surrounding containers impose on what is being emitted.

    `width` is how much room there is across — the text column, or one cell
    of a row — and it is what a table divides between its columns, where a
    right-aligned control lands, and how wide an illustration may be drawn.

    `ids` numbers the drawings of one document and `notes` collects what the
    build has to report; both are shared by the whole walk, so the numbering
    follows reading order and a note can name the task it came from.
    """

    width: int = st.TEXT_WIDTH
    style: str = st.NORMAL
    ids: Ids = field(default_factory=Ids)
    notes: Notes = field(default_factory=Notes)
    task: Optional[int] = None


# --- inline -------------------------------------------------------------


def _ruled(width_px: float) -> str:
    """A place to write: a run of non-breaking spaces with a line under it.

    Not a border and not a tab leader — a run keeps its length when the text
    around it is edited, and a teacher can type the answer straight onto it.
    """
    count = max(1, round(width_px / _NBSP_PX))
    return run(" " * count, underline=True)


def _verdict() -> str:
    box = run("☐", font=st.SYMBOL_FONT)
    return box + run(f' {t("true_label")}  ') + box + run(f' {t("false_label")}')


def _math(model: Math, frame: Frame) -> str:
    """A formula: OMML if it is inside the subset, the author's own text if
    it is not.

    The text is printed with its dollars, so that what is on the sheet is
    what was written — and the reason lands in the notes, because a formula
    that quietly became a line of TeX is exactly the kind of thing a teacher
    finds after printing thirty copies.
    """
    fence = "$$" if model.display else "$"
    xml, reason = convert(model.latex, display=model.display)
    if xml is not None:
        return xml
    where = f"задание {frame.task}: " if frame.task is not None else ""
    frame.notes.add(f"{where}{fence}{model.latex}{fence} — {reason}")
    return run(f"{fence}{model.latex}{fence}")


def _piece(part: Inline, frame: Frame) -> str:
    if isinstance(part, Run):
        return run(part.text, script=part.script)
    if isinstance(part, Math):
        return _math(part, frame)
    if isinstance(part, Blank):
        return _ruled(part.width_ch * _CH_PX)
    if isinstance(part, Gap):
        return _ruled(_GAP_PX)
    if isinstance(part, Slot):
        return _ruled(part.width_px)
    if isinstance(part, Square):
        return run("☐", font=st.SYMBOL_FONT)
    if isinstance(part, Verdict):
        return _verdict()
    raise Unsupported(f"инлайн-элемент '{type(part).__name__}' не печатается в Word")


def inline(runs: Text, frame: Frame) -> str:
    return "".join(_piece(part, frame) for part in runs)


# --- adjusting what children produced -----------------------------------


def _shift(nodes: list[Node], amount: int) -> list[Node]:
    for node in nodes:
        node.indent += amount
    return nodes


def _gap_after(nodes: list[Node], amount: int) -> list[Node]:
    """The gap belongs to the last paragraph of a block, because in Word there
    is no wrapper to hang it on."""
    if nodes:
        nodes[-1].after = max(nodes[-1].after, amount)
    return nodes


def _label(nodes: list[Node], text: str, gutter: int, style: Optional[str] = None) -> list[Node]:
    """Put a number, a letter or a caption into the margin of the first
    paragraph, and move everything else past it.

    If the block opens with a table there is no first paragraph to put it in,
    so the label gets a line of its own — the alternative would be a number
    silently vanishing.
    """
    marker = run(text, bold=True) + tab_run()
    _shift(nodes, gutter)
    if nodes and isinstance(nodes[0], Par):
        first = nodes[0]
        first.runs = marker + first.runs
        first.hanging = gutter
        if style is not None:
            first.style = style
        return nodes
    return [Par(marker, style=style or st.NORMAL, indent=gutter, hanging=gutter), *nodes]


# --- blocks -------------------------------------------------------------


def _bullet_item(item: Item, marker: str, frame: Frame) -> Par:
    gutter = st.MARKER_GUTTER if marker else 0
    runs = run(marker, bold=True) + tab_run() if marker else ""
    if isinstance(item, Statement):
        # Statement on the left, control at the right edge — the tab does what
        # `justify-content: space-between` does on screen, including keeping
        # the control on the last line when the statement wraps.
        runs += inline(item.runs, frame) + tab_run() + inline((item.control,), frame)
        return Par(runs, style="ListItem", indent=gutter, hanging=gutter, right_tab=frame.width)
    runs += inline(item, frame)
    return Par(runs, style="ListItem", indent=gutter, hanging=gutter)


def _marker(model: Bullets, index: int) -> str:
    if model.marker == "number":
        return f"{index + 1}."
    if model.marker == "letter":
        return f"{LETTERS[index]})"
    return ""


def _bullets(model: Bullets, frame: Frame) -> list[Node]:
    if model.columns == "inline":
        # A row of short items: one paragraph, items a wide space apart.
        pieces = [inline(item, frame) for item in model.items if not isinstance(item, Statement)]
        return [Par(run("   ").join(pieces))]
    if model.columns != "two":
        return [
            _bullet_item(item, _marker(model, i), frame) for i, item in enumerate(model.items)
        ]
    inner = _inner_frame(frame, 2, st.COLUMN_GAP)
    groups: list[list[Node]] = [
        [_bullet_item(item, _marker(model, i), inner)] for i, item in enumerate(model.items)
    ]
    return [_column_table(groups, 2, frame, st.COLUMN_GAP)]


def _inner_frame(frame: Frame, columns: int, gap: int) -> Frame:
    """What a child of a row has to work with: its share of the width, less
    the gutter that separates it from its neighbour.

    Derived from the frame rather than built anew, because `ids` numbers the
    drawings of the whole document: a fresh frame would start counting again
    and two pictures would claim the same `wp:docPr id`.
    """
    return replace(frame, width=frame.width // columns - gap)


def _column_table(groups: list[list[Node]], columns: int, frame: Frame, gap: int) -> Tbl:
    """`groups` laid out in `columns`, filling downwards — the promise
    `layout.column_order` makes to both backends."""
    width = frame.width // columns
    rows = [
        [
            "".join(_xml(node) for node in groups[index]) if index is not None else ""
            for index in line
        ]
        for line in column_order(len(groups), columns)
    ]
    return Tbl(rows, [width] * columns, cell_margin=gap // 2)


def _side_by_side(blocks: tuple[Block, ...], frame: Frame, gap: int) -> Tbl:
    inner = _inner_frame(frame, len(blocks), gap)
    groups = [_block(child, inner) for child in blocks]
    return _column_table(groups, len(blocks), frame, gap)


def _columns(model: Columns, frame: Frame) -> Tbl:
    if model.columns is None:
        return _side_by_side(model.blocks, frame, st.COLUMN_GAP)
    inner = _inner_frame(frame, model.columns, st.COLUMN_GAP)
    groups = [_block(child, inner) for child in model.blocks]
    return _column_table(groups, model.columns, frame, st.COLUMN_GAP)


def _grid(model: Grid, frame: Frame) -> Tbl:
    columns = max(1, len(model.headers))
    width = frame.width // columns
    header = [
        _xml(Par(inline(header_cell, frame), style="TableCell")) for header_cell in model.headers
    ]
    body = [
        [_xml(Par(inline(item, frame), style="TableCell")) for item in line] for line in model.rows
    ]
    return Tbl(
        [header, *body],
        [width] * columns,
        borders=True,
        header=True,
        cell_margin=st.px(9),
    )


def _answers(model: Answers, frame: Frame) -> list[Node]:
    if not model.rows:
        return []
    nodes: list[Node] = [
        Par("", before=st.SECTION_GAP, after=0, border_bottom=True),
        Par(run(t("answers_title"), bold=True), style="AnswersTitle"),
    ]
    for answer in model.rows:
        body = _blocks(answer.blocks, replace(frame, style="AnswerItem"))
        if answer.explanation is not None:
            body.append(
                Par(
                    run(f'{t("explanation_label")} ', bold=True) + inline(answer.explanation, frame),
                    style="Explanation",
                )
            )
        if not body:
            body = [Par("", style="AnswerItem")]
        nodes.extend(_label(body, answer.caption, st.ANSWER_GUTTER, style="AnswerItem"))
    return nodes


def _drawing(model: Picture, frame: Frame) -> str:
    """A picture, with the drawing layer's refusal turned into this backend's.

    The two layers have an `Unsupported` each — one is about a node, the other
    about a block — and only this one reaches the CLI. Without the translation
    a type that brings a node with no second serialiser (or a `Raw`) would
    reach a teacher as a traceback instead of a sentence, which is the one
    thing the refusal exists to prevent.
    """
    try:
        return drawing(model.model, width_twips=frame.width, ids=frame.ids)
    except DrawUnsupported as error:
        where = f" в задании {frame.task}" if frame.task is not None else ""
        raise Unsupported(f"иллюстрация{where} не печатается в Word: {error}") from error


def _block(model: Block, frame: Frame) -> list[Node]:
    if isinstance(model, (Para, Phrase, Line)):
        return [Par(inline(model.runs, frame), style=frame.style)]
    if isinstance(model, Hint):
        return [Par(inline(model.runs, frame), style="Hint")]
    if isinstance(model, Heading):
        return [Par(inline(model.runs, frame), style="SheetTitle" if model.level == 1 else "SectionTitle")]
    if isinstance(model, Rule):
        return [Par("", before=st.px(15), after=st.px(23), border_bottom=True)]
    if isinstance(model, Bullets):
        return _bullets(model, frame)
    if isinstance(model, Lines):
        return [Par(inline(line, frame), style=frame.style) for line in model.rows]
    if isinstance(model, Grid):
        return [_grid(model, frame)]
    if isinstance(model, Bank):
        return [Par(
            run(model.label, bold=True)
            + run(" ")
            + run(", ").join(inline(item, frame) for item in model.items),
            style="Bank",
        )]
    if isinstance(model, Picture):
        # A drawing is a run, so it needs a paragraph of its own: it stands on
        # the sheet as a block, exactly as it does on the page.
        return [Par(_drawing(model, frame))]
    if isinstance(model, Spaced):
        return _gap_after(_block(model.block, frame), st.BLOCK_GAP)
    if isinstance(model, Stack):
        return _blocks(model.blocks, frame)
    if isinstance(model, Columns):
        return [_columns(model, frame)]
    if isinstance(model, Facing):
        return [_side_by_side(model.blocks, frame, st.FACING_GAP)]
    if isinstance(model, Numbered):
        # Paragraphs of a task carry a style of their own, so that a teacher
        # can change how every task on the sheet reads in one place.
        body = _blocks(model.blocks, replace(frame, style="Task", task=model.number))
        return _gap_after(_label(body, f"{model.number}.", st.TASK_GUTTER), st.TASK_GAP)
    if isinstance(model, Lettered):
        body = _shift(_blocks(model.blocks, replace(frame, style="Subtask")), st.SUBTASK_INDENT)
        if model.letter:
            body = _label(body, f"{model.letter})", st.LETTER_GUTTER)
        return _gap_after(body, st.BLOCK_GAP)
    if isinstance(model, Answers):
        return _answers(model, frame)
    raise Unsupported(f"блок '{type(model).__name__}' не печатается в Word")


def _blocks(blocks: tuple[Block, ...], frame: Frame) -> list[Node]:
    nodes: list[Node] = []
    for block in blocks:
        nodes.extend(_block(block, frame))
    return nodes


# --- serialising --------------------------------------------------------


def _xml(node: Node) -> str:
    if isinstance(node, Par):
        return para(
            node.runs,
            style=node.style if node.style != st.NORMAL else None,
            indent=node.indent,
            hanging=node.hanging,
            before=node.before,
            after=node.after,
            right_tab=node.right_tab,
            border_bottom=node.border_bottom,
        )
    rows = "".join(
        row(
            "".join(
                cell(content, width=width, shade="EEEEEE" if node.header and i == 0 else None)
                for content, width in zip(line, node.widths)
            ),
            header=node.header and i == 0,
        )
        for i, line in enumerate(node.rows)
    )
    body = table(
        rows,
        widths=node.widths,
        borders=node.borders,
        indent=node.indent,
        cell_margin=node.cell_margin,
    )
    # A table cannot carry spacing of its own: in Word that is a property of a
    # paragraph, so the gap after a table is an empty paragraph.
    if node.after:
        body += para("", after=node.after)
    return body


def body_xml(blocks: tuple[Block, ...]) -> tuple[str, tuple[str, ...]]:
    """The `w:body` content for a whole document, and what the build has to
    say about it.

    The body always ends with a paragraph. Word itself never writes a table
    as the last thing before `w:sectPr` — it keeps an empty paragraph there —
    and a document that does gets «обнаружены ошибки» on opening. The same
    rule `cell()` follows one level down; a document that ends with a
    two-column row (a summary, a handout without answers) is exactly where it
    was missing.
    """
    frame = Frame()
    nodes = _blocks(blocks, frame)
    if not nodes or isinstance(nodes[-1], Tbl):
        nodes.append(Par(""))
    return "".join(_xml(node) for node in nodes) + st.section_xml(), frame.notes.items
