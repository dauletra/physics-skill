"""A formula on a slide: the same OMML a sheet carries, in a slide's envelope.

The maths itself is `ooxml/omml.py` and is not touched here — a fraction is
written with the same elements wherever it goes, which is the whole reason
that module moved out of the Word backend. What differs is what wraps it.

**Word puts a formula straight into a paragraph. PowerPoint does not.** A
slide's paragraph holds runs of DrawingML text, and maths reaches it through
the markup-compatibility mechanism: `mc:AlternateContent` offers the equation
to a reader that understands the 2010 drawing extension, and plain text to
one that does not. That fallback is not ceremony — it is what a version of
PowerPoint older than 2010, and every converter that is not PowerPoint, will
show instead of nothing.

**And the compromise this closes.** The player set formulas with KaTeX from a
CDN, which meant a lesson with a formula needed the internet to be shown at
all (CLAUDE.md, «Известные компромиссы»). A deck carries its formulas inside
itself.
"""

from __future__ import annotations

from physics_svg.ooxml import el
from physics_svg.ooxml.omml import convert

#: Markup compatibility, and the extension that carries maths on a slide.
_MC = "http://schemas.openxmlformats.org/markup-compatibility/2006"
_A14 = "http://schemas.microsoft.com/office/drawing/2010/main"

#: OMML's own namespace, and the Word one its runs carry their font in.
#: A slide part declares neither, so the formula brings both with it.
_M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def formula(latex: str, fallback: str, *, display: bool = False) -> tuple[str, str]:
    """A formula for a slide paragraph: (xml, note).

    The note is empty when the formula converted. When it did not — the
    subset is closed and a formula outside it is not guessed at — the xml is
    empty too, and the caller prints the author's own text instead. Silence
    would put `\\int` on the screen in the middle of a lesson.
    """
    body, reason = convert(latex, display=display)
    if body is None:
        return "", reason
    return _alternate(_with_namespaces(body), fallback), ""


def _with_namespaces(body: str) -> str:
    """The namespaces a slide has never heard of, declared on the formula.

    A `.docx` declares them once on its root; a slide part cannot, because
    nothing else in it speaks either language. Declaring them here keeps the
    change local to the formula and leaves every other part alone.
    """
    opening = body.index(">")
    return f'{body[:opening]} xmlns:m="{_M}" xmlns:w="{_W}"{body[opening:]}'


def _alternate(math: str, fallback: str) -> str:
    return el(
        "mc:AlternateContent",
        {"xmlns:mc": _MC},
        el("mc:Choice", {"xmlns:a14": _A14, "Requires": "a14"}, el("a14:m", children=math))
        + el("mc:Fallback", children=fallback),
    )
