"""Author text as DrawingML paragraphs.

The counterpart of `document/emit/docx/wml.py:run()`, one vocabulary over:
Word sets text in `w:p`/`w:r`, everything on a slide is set in `a:p`/`a:r`.
The parsing is not repeated — `inline.py` has already turned the author's
line into runs, and this module only writes them down.

Two things DrawingML does differently from WordprocessingML and both bite:

* **A superscript is a percentage, not a flag.** `w:vertAlign` names the
  position; `a:rPr baseline` is a per-mille offset, and the run keeps its
  own size unless it is also made smaller. So an index has to carry both.
* **`a:endParaRPr` matters.** A paragraph whose properties live only on its
  runs loses them when the teacher puts the caret at the end and types.
  Copying the paragraph's own size there is what makes an edited slide keep
  looking like the rest of the deck.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from physics_svg.inline import Blank, Math, Run, Text, parse_inline
from physics_svg.ooxml import el, escape
from physics_svg.presentation.pptx import design

#: How far an index sits off the baseline, in per mille, and how much of the
#: parent size it keeps. The ratio is the one the SVG uses (`draw/text.py`),
#: so an index looks the same on a slide as on the picture beside it.
_SUPER = 30000
_SUB = -25000
_SCRIPT_RATIO = 0.72


@dataclass(frozen=True)
class Style:
    """How one paragraph is set. Sizes are in points; `None` inherits from
    the placeholder, which is where a slide's defaults belong."""

    size: Optional[float] = None
    colour: Optional[str] = None
    bold: bool = False
    align: Optional[str] = None  # ctr | r — left is the default
    #: Space above the paragraph, in points.
    space_before: Optional[float] = None
    #: Line spacing as a multiple of the size.
    leading: Optional[float] = None
    #: A bulleted item; `None` leaves the placeholder's own bullet rule.
    bullet: Optional[bool] = None
    #: A numbered item. PowerPoint numbers it itself, which is the point: a
    #: teacher who inserts a step of a worked example gets the rest
    #: renumbered instead of a list that lies.
    numbered: bool = False


def _run_properties(style: Style, script: str = "") -> str:
    attrs: dict[str, object] = {"lang": "ru-RU", "dirty": "0"}
    size = style.size
    if script:
        attrs["baseline"] = _SUPER if script == "sup" else _SUB
        if size is not None:
            size = size * _SCRIPT_RATIO
    if size is not None:
        attrs["sz"] = design.sz(size)
    if style.bold:
        attrs["b"] = 1
    fill = (
        el("a:solidFill", children=el("a:srgbClr", {"val": style.colour}))
        if style.colour
        else ""
    )
    return el("a:rPr", attrs, fill)


def _paragraph_properties(style: Style) -> str:
    attrs: dict[str, object] = {}
    if style.align:
        attrs["algn"] = style.align
    body = ""
    if style.space_before is not None:
        body += el(
            "a:spcBef",
            children=el("a:spcPts", {"val": design.sz(style.space_before)}),
        )
    if style.leading is not None:
        body = el(
            "a:lnSpc",
            children=el("a:spcPct", {"val": round(style.leading * 100000)}),
        ) + body
    if style.bullet is not None:
        # An explicit «no bullet» is needed as often as a bullet: a heading
        # inside a body placeholder inherits one otherwise.
        #
        # The indent is not decoration either. A bullet with no hanging
        # indent puts the second line of an item under its dash, and a list
        # read from eight metres stops looking like a list.
        if style.bullet:
            hang = design.emu((style.size or design.TEXT) * 1.2)
            attrs["marL"] = hang
            attrs["indent"] = -hang
            body += el("a:buChar", {"char": "—"})
        else:
            attrs["marL"] = 0
            attrs["indent"] = 0
            body += el("a:buNone")
    if style.numbered:
        hang = design.emu((style.size or design.TEXT) * 1.4)
        attrs["marL"] = hang
        attrs["indent"] = -hang
        body += el("a:buAutoNum", {"type": "arabicPeriod"})
    return el("a:pPr", attrs, body) if attrs or body else ""


def paragraph(raw: object, style: Style = Style(), notes: Optional[list[str]] = None) -> str:
    """One line of author text as `a:p`.

    A ruled blank is a document control and has no meaning on a slide:
    nothing on the screen is written on.

    `notes` collects what a formula could not say — see `_math`. Passing
    `None` means nobody is listening, which is right for a heading and wrong
    for anything that carries author maths.
    """
    pieces = parse_inline(raw)
    return runs_paragraph(pieces, style, notes)


def runs_paragraph(
    pieces: Sequence[object], style: Style = Style(), notes: Optional[list[str]] = None
) -> str:
    return joined_paragraph([(pieces, style)], style, notes)


def joined_paragraph(
    parts: Sequence[tuple[Sequence[object], Style]],
    style: Style = Style(),
    notes: Optional[list[str]] = None,
) -> str:
    """One line whose parts are set differently — a label and what it labels.

    «Ответ: 12 с» is one line and two voices: the word is auxiliary and the
    value is the point. Two paragraphs would stack them; two shapes would put
    the gap between them at somebody's discretion. So the paragraph keeps one
    set of paragraph properties — indent, bullet, leading, which belong to the
    line — and each part brings its own run properties.
    """
    body = _paragraph_properties(style)
    for pieces, part_style in parts:
        for piece in pieces:
            if isinstance(piece, Run):
                body += _text_run(piece.text, part_style, piece.script)
            elif isinstance(piece, Math):
                body += _math(piece, part_style, notes)
            elif isinstance(piece, Blank):
                body += _text_run(" ", part_style)
    body += el("a:endParaRPr", {"lang": "ru-RU"} if style.size is None else {
        "lang": "ru-RU",
        "sz": design.sz(style.size),
    })
    return el("a:p", children=body)


def _math(piece: Math, style: Style, notes: Optional[list[str]]) -> str:
    """A formula, as a formula — or as the author's own text, said out loud.

    The fallback is the text with its dollars still on it: what reaches the
    screen is then exactly what was typed, and the reason lands in `notes`.
    A formula that quietly became a line of TeX is the kind of thing a
    teacher discovers with the class already looking at it.
    """
    from physics_svg.presentation.pptx.math import formula

    fence = "$$" if piece.display else "$"
    plain = f"{fence}{piece.latex}{fence}"
    xml, reason = formula(piece.latex, _text_run(plain, style), display=piece.display)
    if xml:
        return xml
    if notes is not None:
        notes.append(f"{plain} — {reason}")
    return _text_run(plain, style)


def _text_run(text: str, style: Style, script: str = "") -> str:
    """One run of slide text.

    No `xml:space` on `a:t`, unlike `w:t` next door: DrawingML has no
    attributes on that element at all, and PowerPoint refuses to open a deck
    that puts one there. It is not needed either — a slide keeps the spaces
    it is given; it is Word that eats them.
    """
    return el(
        "a:r",
        children=_run_properties(style, script) + el("a:t", None, escape(text)),
    )


def empty_paragraph(style: Style = Style()) -> str:
    """A paragraph with nothing in it — what an empty placeholder holds so
    that PowerPoint shows its prompt instead of collapsing it."""
    return el("a:p", children=_paragraph_properties(style))


def text_body(paragraphs: Sequence[str], *, anchor: str = "t", wrap: bool = True) -> str:
    """`p:txBody` — the paragraphs plus how the box holds them.

    `normAutofit` is on by design: PowerPoint decides what to do with text
    that does not fit, and without it the text simply leaves the slide. The
    player refused autofit because it could measure; here nothing can
    (docs/pptx.md §6.3).
    """
    body = el(
        "a:bodyPr",
        {"wrap": "square" if wrap else "none", "anchor": anchor},
        el("a:normAutofit"),
    )
    return el("p:txBody", children=body + el("a:lstStyle") + "".join(paragraphs))


def lines(raw: Text) -> list[str]:
    """Author text already parsed, as one paragraph — the shape callers with
    a `Text` need."""
    return [runs_paragraph(raw)]
