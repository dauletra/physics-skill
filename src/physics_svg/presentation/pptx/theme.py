"""`ppt/theme/theme1.xml` — the palette and the font of the deck.

A theme is where PowerPoint expects the design to live, and putting it there
is what makes the result a real deck rather than a picture of one: the
teacher who opens the file gets our colours in the colour picker and our
font already chosen, and a shape drawn by hand lands on the same palette.

PowerPoint is strict about the shape of `a:fmtScheme`: exactly three fills,
three line styles, three effect styles and three background fills, in that
order. Fewer, and the file does not open. What they *contain* barely matters
for us — nothing in the deck asks for style number two — so they are the
plainest three that satisfy the schema.
"""

from __future__ import annotations

from physics_svg.ooxml import el
from physics_svg.presentation.pptx import design

A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"


def _srgb(value: str) -> str:
    return el("a:srgbClr", {"val": value})


def _colours() -> str:
    """The scheme, in the order OOXML fixes: dark/light pairs, six accents,
    two link colours.

    `dk1`/`lt1` are the text and the paper — that is what the colour map on
    the master turns into `tx1`/`bg1`. The accents past the first hold the
    rest of the palette: the theme has six slots and no way to leave one
    empty, and a grey that the deck actually uses is a better filler than a
    hue nobody asked for.
    """
    entries = [
        ("a:dk1", design.INK),
        ("a:lt1", design.PAPER),
        ("a:dk2", design.PANEL),
        ("a:lt2", design.PAPER_SUNK),
        ("a:accent1", design.ACCENT),
        ("a:accent2", design.ACCENT_LINE),
        ("a:accent3", design.ACCENT_SOFT),
        ("a:accent4", design.INK_SOFT),
        ("a:accent5", design.INK_FAINT),
        ("a:accent6", design.LINE),
        ("a:hlink", design.ACCENT),
        ("a:folHlink", design.INK_FAINT),
    ]
    body = "".join(el(tag, children=_srgb(value)) for tag, value in entries)
    return el("a:clrScheme", {"name": "Урок"}, body)


def _fonts() -> str:
    face = el("a:latin", {"typeface": design.FONT}) + el("a:ea", {"typeface": ""}) + el(
        "a:cs", {"typeface": ""}
    )
    return el(
        "a:fontScheme",
        {"name": "Урок"},
        el("a:majorFont", children=face) + el("a:minorFont", children=face),
    )


def _formats() -> str:
    fill = el("a:solidFill", children=el("a:schemeClr", {"val": "phClr"}))
    lines = "".join(
        el(
            "a:ln",
            {"w": width, "cap": "flat", "cmpd": "sng", "algn": "ctr"},
            fill + el("a:prstDash", {"val": "solid"}),
        )
        for width in (6350, 12700, 19050)
    )
    effects = el("a:effectStyle", children=el("a:effectLst")) * 3
    return el(
        "a:fmtScheme",
        {"name": "Урок"},
        el("a:fillStyleLst", children=fill * 3)
        + el("a:lnStyleLst", children=lines)
        + el("a:effectStyleLst", children=effects)
        + el("a:bgFillStyleLst", children=fill * 3),
    )


def theme() -> str:
    return el(
        "a:theme",
        {"xmlns:a": A_NS, "name": "Урок"},
        el("a:themeElements", children=_colours() + _fonts() + _formats())
        + el("a:objectDefaults")
        + el("a:extraClrSchemeLst"),
    )
