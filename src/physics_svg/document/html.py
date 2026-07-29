"""HTML fragments shared by components and questions.

The escaping rule is the project's, restated for markup: specs hold **raw
author text**, and `esc()` is called at the point of interpolation. The
helpers here take markup that is already safe — a caller hands them escaped
text, or rows it has assembled itself with checkboxes in them — which is why
they never escape a second time.

One visual language for lists: options, statements, ranked items and plain
bullets are all `list_html`, so a document does not sprout four ways of
showing a series of things.
"""

from __future__ import annotations

from physics_svg.document.strings import LETTERS, t
from physics_svg.draw import esc


def div(class_name: str, content: str) -> str:
    return f'<div class="{class_name}">{content}</div>'


def list_html(items: list[str], marker: str = "none", columns: str = "single") -> str:
    """A series of items with an optional marker. `items` are safe markup."""

    def marker_html(i: int) -> str:
        if marker == "number":
            return f'<span class="list-marker">{i + 1}.</span>'
        if marker == "letter":
            return f'<span class="list-marker">{LETTERS[i]})</span>'
        return ""

    rows = "".join(
        f'<div class="list-row">{marker_html(i)}'
        f'<span class="list-content">{item}</span></div>'
        for i, item in enumerate(items)
    )
    return f'<div class="list-component cols-{columns}">{rows}</div>'


def table_html(headers: list[str], rows: list[list[str]]) -> str:
    """A real two-dimensional grid with named columns. Cells are safe markup."""
    head = "".join(f"<th>{cell}</th>" for cell in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return (
        '<table class="table-component">'
        f"<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
    )


def blank(width_px: int = 150) -> str:
    """An underlined run for a short written answer."""
    return f'<span class="answer-line" style="min-width:{width_px}px;"></span>'


def blank_cell() -> str:
    """A gap inside a table — the same visual language as a gap in text."""
    return '<span class="fill-blank"></span>'


def bank_list(items: list[str]) -> str:
    """"Words to choose from: …" for `fill_text` and `fill_table`."""
    joined = ", ".join(esc(item) for item in items)
    return f'<div class="bank-list"><strong>{t("bank_label")}</strong> {joined}</div>'


def statement_row(text: str, control: str) -> str:
    """A statement on the left, its answer control on the right — shared by
    `true_false`, `rank` and `classify` so their rows line up."""
    return (
        '<span class="tf-line">'
        f'<span class="tf-statement">{text}</span>{control}</span>'
    )
