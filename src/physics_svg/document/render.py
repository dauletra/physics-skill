"""Models -> layout.

One builder for everything the skill produces: a set of exercises, an
explanation, a lesson summary, or all of them mixed. The genre is a
combination of blocks, not a mode of the builder.

What is decided here is what belongs to the document rather than to any one
format: continuous numbering, subtask letters, which blocks stand beside one
another, and which answers reach the section at the end. What it looks like
is a backend's business — see `document/emit/`.

Answers are never printed in the body. Every question type has a pair of
renderers, and only the second one reaches the answers section — so the
handout variant is this document *without a section*, not a second rendering
that could leak.
"""

from __future__ import annotations

from typing import Any, Callable, NamedTuple, Optional

from physics_svg.document.answers import Block as DrawnAnswer
from physics_svg.document.answers import Inline as ShortAnswer
from physics_svg.document.answers import MaybeAnswer, Rows
from physics_svg.document.components import (
    AnswerLineSpec,
    DividerSpec,
    HeadingSpec,
    ListSpec,
    TableSpec,
    TextSpec,
    build_answer_line,
    build_divider,
    build_heading,
    build_list,
    build_table,
    build_text,
)
from physics_svg.document.containers import (
    DocRowSpec,
    PartSpec,
    RowSpec,
    TaskSpec,
    iter_flat,
    task_part_labels,
)
from physics_svg.document.emit import docx, html, render_source  # noqa: F401  (re-exported)
from physics_svg.document.layout import (
    AnswerRow,
    Answers,
    Block,
    Columns,
    Lettered,
    Lines,
    Numbered,
    Phrase,
    Picture,
    Spaced,
    Stack,
    is_empty,
)
from physics_svg.document.manifest import DocumentSpec
from physics_svg.document.questions import is_question, render_answer, render_body
from physics_svg.inline import parse_inline

_COMPONENT_BUILDERS: dict[type, Callable[[Any], Block]] = {
    TextSpec: build_text,
    TableSpec: build_table,
    ListSpec: build_list,
    AnswerLineSpec: build_answer_line,
    HeadingSpec: build_heading,
    DividerSpec: build_divider,
}


class Builder:
    """Builds the layout of one document.

    It carries a counter because every illustration needs an element id scope
    unique on the page — two rulings on one sheet must not share a pattern id.
    The counter is per build and the walk is deterministic, so the same draft
    always produces the same file.
    """

    def __init__(self) -> None:
        self._visuals = 0

    def _scope(self) -> str:
        self._visuals += 1
        return f"v{self._visuals}"

    # --- leaves ---

    def component(self, model: Any) -> Block:
        builder = _COMPONENT_BUILDERS.get(type(model))
        if builder is not None:
            return builder(model)
        # Everything else is an illustration, straight from the registry.
        return Picture(model, self._scope())

    def leaf(self, model: Any) -> tuple[Block, ...]:
        body = render_body(model) if is_question(model) else self.component(model)
        if is_empty(body):
            # `open` prints nothing in the body (its statement and its writing
            # space are neighbours); an empty wrapper would add vertical space
            # around nothing.
            return ()
        return (Spaced(body),)

    # --- containers ---

    def task_block(self, model: Any, labels: dict[int, str]) -> tuple[Block, ...]:
        if isinstance(model, RowSpec):
            columns = tuple(
                Stack(self.task_block(child, labels)) for child in model.blocks
            )
            return (Columns(columns, model.columns),)
        if isinstance(model, PartSpec):
            body: tuple[Block, ...] = ()
            for child in model.blocks:
                body += self.task_block(child, labels)
            return (Lettered(labels.get(id(model)), body),)
        return self.leaf(model)

    def task(self, number: int, model: TaskSpec) -> Block:
        labels = task_part_labels(model)
        body: tuple[Block, ...] = ()
        for child in model.blocks:
            body += self.task_block(child, labels)
        return Numbered(number, body)

    def doc_block(self, model: Any, number: Optional[int] = None) -> Block:
        if isinstance(model, TaskSpec):
            assert number is not None
            return self.task(number, model)
        if isinstance(model, HeadingSpec):
            return build_heading(model)
        if isinstance(model, DocRowSpec):
            columns = tuple(self.doc_block(child) for child in model.blocks)
            return Columns(columns, model.columns)
        return Spaced(self.component(model))

    # --- answers ---

    def answers(self, numbered_tasks: list[tuple[int, TaskSpec]]) -> Answers:
        """One row per question that has an answer or an explanation ("3." for
        a single question, "3. б)" for a subtask). Tasks with neither are
        skipped, and an empty section is not printed at all — a lesson summary
        simply has none."""
        rows = []
        for number, task in numbered_tasks:
            for label, question in _task_answers(task):
                answer = render_answer(question)
                if answer is None and not question.explanation:
                    continue
                caption = f"{number}." + (f" {label})" if label else "")
                explanation = (
                    parse_inline(question.explanation) if question.explanation else None
                )
                rows.append(AnswerRow(caption, _answer_blocks(answer), explanation))
        return Answers(tuple(rows))


def _answer_blocks(answer: MaybeAnswer) -> tuple[Block, ...]:
    """The one place an answer's shape becomes layout.

    A kind says what it has — a line, a line per element, a drawing — and the
    section decides how that is placed, so answers of different kinds stay
    consistent on the sheet and no kind has to know the section's markup.
    """
    if answer is None:
        return ()
    if isinstance(answer, Rows):
        return (Lines(answer.rows),)
    if isinstance(answer, DrawnAnswer):
        return (answer.block,)
    assert isinstance(answer, ShortAnswer)
    return (Phrase(answer.runs),)


def _task_answers(task: TaskSpec) -> list[tuple[str, Any]]:
    """(letter or empty, question) pairs in order: a single question has no
    letter, a question inside a part carries its part's letter."""
    labels = task_part_labels(task)
    pairs: list[tuple[str, Any]] = []
    for block in iter_flat(task.blocks):
        if is_question(block):
            pairs.append(("", block))
        elif isinstance(block, PartSpec):
            for inner in iter_flat(block.blocks):
                if is_question(inner):
                    pairs.append((labels[id(block)], inner))
    return pairs


def _numbered(blocks: list[Any]) -> list[tuple[Any, Optional[int]]]:
    """Continuous numbering: tasks get 1..N in order of appearance, and other
    blocks do not shift it."""
    result: list[tuple[Any, Optional[int]]] = []
    counter = 0
    for block in blocks:
        if isinstance(block, TaskSpec):
            counter += 1
            result.append((block, counter))
        else:
            result.append((block, None))
    return result


def build_layout(blocks: list[Any], *, with_answers: bool = True) -> tuple[Block, ...]:
    """The document as layout — the input of every backend.

    `with_answers` controls only the section at the end.
    """
    builder = Builder()
    numbered = _numbered(blocks)
    body = tuple(builder.doc_block(block, number) for block, number in numbered)
    if not with_answers:
        return body
    answers = builder.answers(
        [
            (number, block)
            for block, number in numbered
            if isinstance(block, TaskSpec) and number is not None
        ]
    )
    return body + (answers,)


def build_document(
    doc: DocumentSpec,
    blocks: list[Any],
    *,
    with_answers: bool = True,
    source: Optional[dict[str, Any]] = None,
) -> str:
    """The whole document as one HTML file.

    `source` is the raw draft to embed — passed for the full variant only,
    since in a handout it would reveal the answers through the page source.
    """
    return html.page(doc.title, build_layout(blocks, with_answers=with_answers), source)


class Docx(NamedTuple):
    """The file and what the build has to say about it.

    `notes` is not an error list: the document is finished and correct. It is
    what the build could not express in Word and printed as plain text
    instead — today only formulas outside the OMML subset. A pair rather than
    an optional out-parameter, because a report nobody is forced to look at
    is the same thing as no report.
    """

    data: bytes
    notes: tuple[str, ...]


def build_docx(
    doc: DocumentSpec,
    blocks: list[Any],
    *,
    with_answers: bool = True,
) -> Docx:
    """The whole document as one .docx file.

    No embedded draft, unlike HTML: Word rewrites the package when the teacher
    saves, so a promise that the file can be loaded back into a session would
    be a promise we cannot keep. The HTML file remains the way back.
    """
    data, notes = docx.document(doc.title, build_layout(blocks, with_answers=with_answers))
    return Docx(data, notes)


def build_preview(doc: DocumentSpec, blocks: list[Any], block_id: str) -> str:
    """One top-level block in the real styles, under its real number and with
    its own answers — a cheap visual check. No embedded draft: a preview is a
    scratch artefact, not a file to continue a session from."""
    numbered = _numbered(blocks)
    match = next(
        ((block, number) for block, number in numbered if getattr(block, "id", None) == block_id),
        None,
    )
    if match is None:
        raise KeyError(block_id)
    block, number = match
    builder = Builder()
    body: tuple[Block, ...] = (builder.doc_block(block, number),)
    if isinstance(block, TaskSpec) and number is not None:
        body += (builder.answers([(number, block)]),)
    return html.page(doc.title, body)
