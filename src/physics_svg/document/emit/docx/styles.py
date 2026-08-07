"""Page setup and named styles — the Word counterpart of `assets.py::BASE_CSS`.

Two decisions live here, and both are the point of having a Word output at
all.

**The teacher edits styles, not blocks.** Every paragraph the backend emits
carries a named style, and the names are Russian because they show up in
Word's style panel. Changing «Обычный» re-flows the whole sheet — the same
promise the stylesheet makes on screen. Nothing is formatted in place except
what only the content can know (the width of a blank, the number of columns).

**Geometry is converted, not re-guessed.** The HTML sheet is laid out in CSS
pixels at 96 dpi, so one pixel is exactly 0.75 pt — fifteen twips. Every
distance below comes from the stylesheet through `px()`, which is why the
Word sheet has the same rhythm as the page it was translated from instead of
a second set of hand-picked numbers.

Printing *is* engineered here, unlike in HTML: A4, real margins, a table
header that repeats over a page break. That is the whole reason the format
exists.
"""

from __future__ import annotations

from physics_svg.document.emit.docx.wml import P_ORDER, R_ORDER, el, props

#: Twips (1/1440 inch) per CSS pixel at 96 dpi.
_TWIPS_PER_PX = 15


def px(value: float) -> int:
    """A distance from the stylesheet, in twips."""
    return round(value * _TWIPS_PER_PX)


# --- the page -----------------------------------------------------------

PAGE_WIDTH = 11906  # A4, 210 mm
PAGE_HEIGHT = 16838  # A4, 297 mm
MARGIN_X = 1134  # 20 mm
MARGIN_Y = 850  # 15 mm

#: Everything that has to fit across the sheet is measured from this.
TEXT_WIDTH = PAGE_WIDTH - 2 * MARGIN_X

# --- type ---------------------------------------------------------------

#: The first font of the HTML stack, so the printed sheet and the screen one
#: read the same. If it is missing, Word substitutes — and because blanks are
#: measured in characters rather than in points, they scale with it.
FONT = "PT Sans"
#: `☐` is not in every text font; this one ships with Windows and macOS Word.
SYMBOL_FONT = "Segoe UI Symbol"

#: Half-points, from the stylesheet's pt sizes.
SIZE_BODY = 24
SIZE_TITLE = 32
SIZE_SECTION = 27
SIZE_SMALL = 22
SIZE_HINT = 21

#: 1/240 of a line: the stylesheet's `line-height: 1.4`.
LINE = 336

# --- distances ----------------------------------------------------------

BLOCK_GAP = px(11)  # .task-block margin-bottom
TASK_GAP = px(26)  # .task margin-bottom
SUBTASK_INDENT = px(23)  # .task-part margin-left
COLUMN_GAP = px(23)  # .task-row gap
FACING_GAP = px(45)  # .match-columns gap
SECTION_GAP = px(34)  # .answers-section margin-top

#: Gutters: the number, the letter and the marker stand in a margin of their
#: own, and the text of the block lines up past it. Wide enough for the
#: longest thing that goes there — «16.», «3. б)», «а)».
TASK_GUTTER = 480
LETTER_GUTTER = 360
MARKER_GUTTER = 340
ANSWER_GUTTER = 620

#: Width of one non-breaking space at the body size, in pixels. Blanks are
#: built out of them, so this is what turns a CSS width into a character
#: count. One place to tune if a ruled line comes out short.
NBSP_PX = 4.2

# --- styles -------------------------------------------------------------

#: styleId -> (Russian name, paragraph properties, run properties). The id is
#: latin because it is a key; the name is what the teacher sees.
_STYLES: list[tuple[str, str, dict[str, str], dict[str, str]]] = [
    (
        "SheetTitle",
        "Заголовок листа",
        {"w:spacing": el("w:spacing", {"w:after": px(11)})},
        {"w:b": el("w:b"), "w:sz": el("w:sz", {"w:val": SIZE_TITLE})},
    ),
    (
        "SectionTitle",
        "Заголовок раздела",
        {"w:spacing": el("w:spacing", {"w:before": px(20), "w:after": px(8)})},
        {"w:b": el("w:b"), "w:sz": el("w:sz", {"w:val": SIZE_SECTION})},
    ),
    ("Task", "Задание", {}, {}),
    ("Subtask", "Подзадание", {}, {}),
    ("ListItem", "Пункт списка", {}, {}),
    ("Bank", "Банк слов", {}, {"w:sz": el("w:sz", {"w:val": SIZE_SMALL})}),
    (
        "Hint",
        "Подсказка",
        {},
        {"w:i": el("w:i"), "w:sz": el("w:sz", {"w:val": SIZE_HINT})},
    ),
    (
        "TableCell",
        "Ячейка таблицы",
        {"w:jc": el("w:jc", {"w:val": "center"})},
        {"w:sz": el("w:sz", {"w:val": SIZE_SMALL})},
    ),
    (
        "AnswersTitle",
        "Заголовок ответов",
        {"w:spacing": el("w:spacing", {"w:before": px(15), "w:after": px(8)})},
        {"w:b": el("w:b"), "w:sz": el("w:sz", {"w:val": SIZE_SECTION})},
    ),
    ("AnswerItem", "Ответ", {}, {"w:sz": el("w:sz", {"w:val": SIZE_SMALL})}),
    (
        "Explanation",
        "Пояснение",
        {},
        {"w:i": el("w:i"), "w:color": el("w:color", {"w:val": "333333"}), "w:sz": el("w:sz", {"w:val": SIZE_SMALL})},
    ),
]

#: The style every paragraph falls back to.
NORMAL = "Normal"


def _style(style_id: str, name: str, paragraph: dict[str, str], run: dict[str, str]) -> str:
    body = el("w:name", {"w:val": name})
    body += el("w:basedOn", {"w:val": NORMAL})
    body += el("w:qFormat")
    body += props("w:pPr", P_ORDER, paragraph)
    body += props("w:rPr", R_ORDER, run)
    return el("w:style", {"w:type": "paragraph", "w:styleId": style_id}, body)


def styles_xml() -> str:
    """`word/styles.xml`: the defaults plus one entry per named style."""
    run_default = props(
        "w:rPr",
        R_ORDER,
        {
            "w:rFonts": el("w:rFonts", {"w:ascii": FONT, "w:hAnsi": FONT, "w:cs": FONT}),
            "w:sz": el("w:sz", {"w:val": SIZE_BODY}),
            "w:szCs": el("w:szCs", {"w:val": SIZE_BODY}),
            "w:lang": el("w:lang", {"w:val": "ru-RU"}),
        },
    )
    paragraph_default = props(
        "w:pPr",
        P_ORDER,
        {"w:spacing": el("w:spacing", {"w:after": 0, "w:line": LINE, "w:lineRule": "auto"})},
    )
    defaults = el(
        "w:docDefaults",
        children=el("w:rPrDefault", children=run_default)
        + el("w:pPrDefault", children=paragraph_default),
    )
    normal = el(
        "w:style",
        {"w:type": "paragraph", "w:default": "1", "w:styleId": NORMAL},
        el("w:name", {"w:val": "Обычный"}) + el("w:qFormat"),
    )
    entries = "".join(_style(*entry) for entry in _STYLES)
    return el(
        "w:styles",
        {"xmlns:w": W_NAMESPACE},
        defaults + normal + entries,
    )


def section_xml() -> str:
    """`w:sectPr` — the last child of the body, and the only place the sheet
    knows it is A4."""
    return el(
        "w:sectPr",
        children=el("w:pgSz", {"w:w": PAGE_WIDTH, "w:h": PAGE_HEIGHT})
        + el(
            "w:pgMar",
            {
                "w:top": MARGIN_Y,
                "w:right": MARGIN_X,
                "w:bottom": MARGIN_Y,
                "w:left": MARGIN_X,
                "w:header": 0,
                "w:footer": 0,
                "w:gutter": 0,
            },
        ),
    )


def settings_xml() -> str:
    return el(
        "w:settings",
        {"xmlns:w": W_NAMESPACE},
        el("w:defaultTabStop", {"w:val": 708}),
    )


W_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
