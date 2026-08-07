"""Layout -> HTML page.

The document is a plain on-screen page: one centred column of readable width,
white background, pixels. There is no print layout here and none is coming —
printing is what the Word backend is for.

Escaping happens here and only here: the layout carries raw author text, and
`esc()` is the gate to markup. A helper in this module never escapes what it
is handed twice — callers pass safe markup, assembled by the functions above
them in this same file.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Optional

from physics_svg.document.assets import BASE_CSS, KATEX_HEAD
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
    Item,
    Lettered,
    Line,
    Lines,
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
    grid_rows,
)
from physics_svg.document.strings import LETTERS, t
from physics_svg.draw import esc
from physics_svg.visuals import build_svg


def div(class_name: str, content: str, style: str = "") -> str:
    attrs = f' style="{style}"' if style else ""
    return f'<div class="{class_name}"{attrs}>{content}</div>'


def column_style(count: int, columns: int) -> str:
    """The grid rows that make `count` items fill `columns` top to bottom.

    `column-count` would balance by height instead and move an item across the
    fold as soon as one of them wraps to a second line. The count comes from
    the content, which is why it is an inline style and not a class: a
    stylesheet cannot know it.
    """
    return f"grid-template-rows: repeat({grid_rows(count, columns)}, auto);"


# --- inline -------------------------------------------------------------


def _run(model: Run) -> str:
    body = esc(model.text)
    return f"<{model.script}>{body}</{model.script}>" if model.script else body


def _verdict() -> str:
    square = '<span class="tf-square"></span>'
    return (
        '<span class="tf-box">'
        f'{square} {t("true_label")}&nbsp;&nbsp;{square} {t("false_label")}'
        "</span>"
    )


_INLINE: dict[type, Callable[[Any], str]] = {
    Run: _run,
    Blank: lambda model: f'<span class="blank" style="width:{model.width_ch}ch;"></span>',
    Gap: lambda model: '<span class="fill-blank"></span>',
    Slot: lambda model: (
        f'<span class="answer-line" style="min-width:{model.width_px}px;"></span>'
    ),
    Square: lambda model: '<span class="rank-square"></span>',
    Verdict: lambda model: _verdict(),
}


def inline(runs: Text) -> str:
    return "".join(_INLINE[type(part)](part) for part in runs)


# --- blocks -------------------------------------------------------------


def _bullets(model: Bullets) -> str:
    def marker(i: int) -> str:
        if model.marker == "number":
            return f'<span class="list-marker">{i + 1}.</span>'
        if model.marker == "letter":
            return f'<span class="list-marker">{LETTERS[i]})</span>'
        return ""

    rows = "".join(
        f'<div class="list-row">{marker(i)}'
        f'<span class="list-content">{_item(item)}</span></div>'
        for i, item in enumerate(model.items)
    )
    style = column_style(len(model.items), 2) if model.columns == "two" else ""
    return div(f"list-component cols-{model.columns}", rows, style)


def _item(model: Item) -> str:
    if isinstance(model, Statement):
        # Statement on the left, control on the right, so that the rows of
        # true_false, rank and classify line up with one another.
        return (
            '<span class="tf-line">'
            f'<span class="tf-statement">{inline(model.runs)}</span>'
            f"{inline((model.control,))}</span>"
        )
    return inline(model)


def _grid(model: Grid) -> str:
    head = "".join(f"<th>{inline(cell)}</th>" for cell in model.headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{inline(cell)}</td>" for cell in row) + "</tr>"
        for row in model.rows
    )
    return (
        '<table class="table-component">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def _columns(model: Columns) -> str:
    """Class and style of a row: without an explicit count every child claims
    a column of its own, which is what the bare grid already does."""
    body = "".join(div("task-col", block(child)) for child in model.blocks)
    if model.columns is None:
        return div("task-row", body)
    return div(
        f"task-row cols-{model.columns}",
        body,
        column_style(len(model.blocks), model.columns),
    )


def _numbered(model: Numbered) -> str:
    # The number stands beside the whole task, in a gutter of its own: the
    # wording, the picture and the ruling are all equally "task 3", and a
    # number sitting on top of the first block would claim only that block.
    return div(
        "task",
        f'<span class="task-num">{model.number}.</span>'
        + div("task-blocks", _blocks(model.blocks)),
    )


def _lettered(model: Lettered) -> str:
    label = f'<span class="subtask-label">{esc(model.letter)})</span>' if model.letter else ""
    return div("task-part", label + div("task-blocks", _blocks(model.blocks)))


def _answers(model: Answers) -> str:
    """One line per question that has an answer or an explanation. An empty
    section is not printed at all — a lesson summary simply has none."""
    if not model.rows:
        return ""
    items = []
    for row in model.rows:
        body = _blocks(row.blocks)
        if row.explanation is not None:
            body += div(
                "answers-explanation",
                f'<strong>{t("explanation_label")}</strong> {inline(row.explanation)}',
            )
        items.append(
            f'<div class="answers-item"><span class="answers-num">{esc(row.caption)}</span>'
            f'{div("answers-body", body)}</div>'
        )
    return div(
        "answers-section",
        div("answers-title", t("answers_title")) + "".join(items),
    )


_BLOCK: dict[type, Callable[[Any], str]] = {
    Para: lambda model: f"<p>{inline(model.runs)}</p>",
    Phrase: lambda model: inline(model.runs),
    Line: lambda model: f"<div>{inline(model.runs)}</div>",
    Hint: lambda model: div("choice-hint", inline(model.runs)),
    Heading: lambda model: div(f"doc-heading level-{model.level}", inline(model.runs)),
    Rule: lambda model: '<hr class="doc-divider">',
    Bullets: _bullets,
    Lines: lambda model: div(
        "answers-rows", "".join(f"<div>{inline(row)}</div>" for row in model.rows)
    ),
    Grid: _grid,
    Bank: lambda model: (
        f'<div class="bank-list"><strong>{model.label}</strong> '
        + ", ".join(inline(item) for item in model.items)
        + "</div>"
    ),
    Picture: lambda model: build_svg(model.model, scope=model.scope),
    Spaced: lambda model: div("task-block", block(model.block)),
    Stack: lambda model: _blocks(model.blocks),
    Columns: _columns,
    Facing: lambda model: div("match-columns", _blocks(model.blocks)),
    Numbered: _numbered,
    Lettered: _lettered,
    Answers: _answers,
}


def block(model: Block) -> str:
    return _BLOCK[type(model)](model)


def _blocks(blocks: tuple[Block, ...]) -> str:
    return "".join(block(child) for child in blocks)


# --- the page -----------------------------------------------------------


def render_source(source: dict[str, Any]) -> str:
    """The draft embedded in the page: the finished file *is* the draft, and
    a new session only has to load it back.

    Every `<` becomes `\\u003c` — a valid JSON escape — so that no author text
    can close the `</script>` tag early.
    """
    payload = json.dumps(source, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id="document-source">{payload}</script>'


def page(
    title: str,
    blocks: tuple[Block, ...],
    source: Optional[dict[str, Any]] = None,
) -> str:
    """The whole document as one self-contained HTML file."""
    source_html = f"\n{render_source(source)}" if source is not None else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{esc(title or t("default_title"))}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{_blocks(blocks)}{source_html}
</body>
</html>"""
