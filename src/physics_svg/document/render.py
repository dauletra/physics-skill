"""Assembling the HTML document.

One builder for everything the skill produces: a set of exercises, an
explanation, a lesson summary, or all of them mixed. The genre is a
combination of blocks, not a mode of the renderer.

Answers are never printed in the body. Every question type has a pair of
renderers, and only the second one reaches the answers section at the end —
so the handout variant is this document *without a section*, not a second
rendering that could leak.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from physics_svg.document.answers import MaybeAnswer, Rows
from physics_svg.document.assets import BASE_CSS, KATEX_HEAD
from physics_svg.document.components import (
    AnswerLineSpec,
    HeadingSpec,
    ListSpec,
    TableSpec,
    TextSpec,
    render_answer_line,
    render_heading,
    render_list,
    render_table,
    render_text,
)
from physics_svg.document.containers import (
    DocRowSpec,
    PartSpec,
    RowSpec,
    TaskSpec,
    iter_flat,
    task_part_labels,
)
from physics_svg.document.html import column_rows, div
from physics_svg.document.manifest import DocumentSpec
from physics_svg.document.questions import is_question, render_answer, render_body
from physics_svg.document.strings import t
from physics_svg.draw import esc
from physics_svg.visuals import build_svg

_COMPONENT_RENDERERS: dict[type, Callable[[Any], str]] = {
    TextSpec: render_text,
    TableSpec: render_table,
    ListSpec: render_list,
    AnswerLineSpec: render_answer_line,
    HeadingSpec: render_heading,
}


class Renderer:
    """Renders one document.

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

    def component(self, model: Any) -> str:
        renderer = _COMPONENT_RENDERERS.get(type(model))
        if renderer is not None:
            return renderer(model)
        return build_svg(model, scope=self._scope())

    def leaf(self, model: Any) -> str:
        body = render_body(model) if is_question(model) else self.component(model)
        if not body:
            # `open` prints nothing in the body (its statement and its writing
            # space are neighbours); an empty wrapper would add vertical space
            # around nothing.
            return ""
        return div("task-block", body)

    # --- containers ---

    def task_block(self, model: Any, labels: dict[int, str]) -> str:
        if isinstance(model, RowSpec):
            columns = "".join(
                div("task-col", self.task_block(child, labels)) for child in model.blocks
            )
            class_name, style = _row_layout(model)
            return div(class_name, columns, style)
        if isinstance(model, PartSpec):
            header = _label_line(labels.get(id(model)))
            inner = "".join(self.task_block(child, labels) for child in model.blocks)
            return div("task-part", header + inner)
        return self.leaf(model)

    def task(self, number: int, model: TaskSpec) -> str:
        labels = task_part_labels(model)
        parts = [_number_line(number)]
        parts += [self.task_block(block, labels) for block in model.blocks]
        return div("task", div("task-blocks", "".join(parts)))

    def doc_block(self, model: Any, number: Optional[int] = None) -> str:
        if isinstance(model, TaskSpec):
            assert number is not None
            return self.task(number, model)
        if isinstance(model, HeadingSpec):
            return render_heading(model)
        if isinstance(model, DocRowSpec):
            columns = "".join(div("task-col", self.doc_block(child)) for child in model.blocks)
            class_name, style = _row_layout(model)
            return div(class_name, columns, style)
        return div("task-block", self.component(model))

    # --- answers ---

    def answers(self, numbered_tasks: list[tuple[int, TaskSpec]]) -> str:
        """One line per question that has an answer or an explanation ("3." for
        a single question, "3. б)" for a subtask). Tasks with neither are
        skipped, and an empty section is not printed at all — a lesson summary
        simply has none."""
        items = []
        for number, task in numbered_tasks:
            for label, question in _task_answers(task):
                answer = render_answer(question)
                if answer is None and not question.explanation:
                    continue
                caption = f"{number}." + (f" {esc(label)})" if label else "")
                body = _answer_html(answer)
                if question.explanation:
                    body += div(
                        "answers-explanation",
                        f'<strong>{t("explanation_label")}</strong> '
                        f"{esc(question.explanation)}",
                    )
                items.append(
                    f'<div class="answers-item"><span class="answers-num">{caption}</span>'
                    f'{div("answers-body", body)}</div>'
                )
        if not items:
            return ""
        return div(
            "answers-section",
            div("answers-title", t("answers_title")) + "".join(items),
        )


def _row_layout(model: RowSpec | DocRowSpec) -> tuple[str, str]:
    """Class and style of a row: without an explicit count every child claims a
    column of its own, which is what the bare grid already does."""
    if model.columns is None:
        return "task-row", ""
    return (
        f"task-row cols-{model.columns}",
        column_rows(len(model.blocks), model.columns),
    )


def _answer_html(answer: MaybeAnswer) -> str:
    """The one place an answer's shape becomes markup.

    A kind says what it has — a line, a line per element, a drawing — and the
    section decides how it looks, so answers of different kinds stay
    consistent on the sheet and no kind has to know the section's markup.
    """
    if answer is None:
        return ""
    if isinstance(answer, Rows):
        return div("answers-rows", "".join(f"<div>{row}</div>" for row in answer.rows))
    return answer.html  # Inline and Block both carry ready markup


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


def _number_line(number: int) -> str:
    # The task number is always a line of its own. The wording of the task is
    # not part of it: that is an ordinary `text` block among the children.
    return div("task-header", f'<span class="task-num">{number}.</span>')


def _label_line(label: Optional[str]) -> str:
    if not label:
        return ""
    return div("task-header", f'<span class="subtask-label">{esc(label)})</span>')


def render_header(doc: DocumentSpec) -> str:
    """Title always (if set); the questionnaire line, subtitle and
    instructions only when the manifest carries a `header`."""
    header = doc.header
    if not doc.title and header is None:
        return ""
    parts = ['<div class="sheet-header">']
    if header is not None:
        parts.append(
            f'<div class="meta-line">{t("school_class")} '
            f'<span class="blank">{esc(header.school)}</span>'
            f' {t("date")} <span class="blank">{esc(header.date)}</span>'
            f' {t("full_name")} <span class="blank" style="min-width:225px;"></span></div>'
        )
    if doc.title:
        parts.append(div("sheet-title", esc(doc.title)))
    if header is not None:
        # Built only from what is filled in: empty subject/grade leave no
        # dangling separator and no stray "класс".
        bits = []
        if header.subject:
            bits.append(esc(header.subject))
        if header.grade:
            bits.append(f'{esc(header.grade)} {t("grade_suffix")}')
        if bits:
            parts.append(div("sheet-subtitle", " &middot; ".join(bits)))
        if header.instructions:
            parts.append(div("sheet-instructions", esc(header.instructions)))
    parts.append("</div>")
    return "".join(parts)


def render_source(source: dict[str, Any]) -> str:
    """The draft embedded in the page: the finished file *is* the draft, and
    a new session only has to load it back.

    Every `<` becomes `\\u003c` — a valid JSON escape — so that no author text
    can close the `</script>` tag early.
    """
    payload = json.dumps(source, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id="document-source">{payload}</script>'


def _page(title: str, body: str, source_html: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{esc(title or t("default_title"))}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{body}{source_html}
</body>
</html>"""


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


def build_document(
    doc: DocumentSpec,
    blocks: list[Any],
    *,
    with_answers: bool = True,
    source: Optional[dict[str, Any]] = None,
) -> str:
    """The whole document as one HTML file.

    `with_answers` controls only the section at the end. `source` is the raw
    draft to embed — passed for the full variant only, since in a handout it
    would reveal the answers through the page source.
    """
    renderer = Renderer()
    numbered = _numbered(blocks)
    body = [render_header(doc)]
    body += [renderer.doc_block(block, number) for block, number in numbered]
    if with_answers:
        body.append(
            renderer.answers(
                [(number, block) for block, number in numbered
                 if isinstance(block, TaskSpec) and number is not None]
            )
        )
    source_html = f"\n{render_source(source)}" if source is not None else ""
    return _page(doc.title, "".join(body), source_html)


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
    renderer = Renderer()
    body = renderer.doc_block(block, number)
    if isinstance(block, TaskSpec) and number is not None:
        body += renderer.answers([(number, block)])
    return _page(doc.title, body)
