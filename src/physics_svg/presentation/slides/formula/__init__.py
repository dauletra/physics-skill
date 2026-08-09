"""A formula said large, with its symbols spelled out underneath.

Why this is a kind and not a `content` slide with a paragraph: the player
has to know which string is *the formula*. Inside a paragraph KaTeX sets it
in text style — a fraction shrinks to fit the line and stops being readable
from the back row. Here the formula is a field of its own, so the player can
give it display style and the height it needs, and the symbols get the shape
they actually have: a pair «обозначение — что это», not a list of sentences
(docs/slide-templates.md §5).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from physics_svg.inline import Math, parse_inline
from physics_svg.presentation.emit import runs
from physics_svg.presentation.pptx import Slide, layouts
from physics_svg.presentation.pptx.text import paragraph, runs_paragraph
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec

#: The genre, for a slide that has no heading of its own to name it.
KICKER = "Формула"


@spec
class TermSpec:
    """Обозначение из формулы и его расшифровка."""

    symbol: str = field(doc="Обозначение как в формуле, в тех же $…$: $\\upsilon_0$, $a$")
    meaning: str = field(doc="Что оно значит: «начальная скорость»")


@spec
class FormulaSpec:
    """Слайд с формулой: сама формула крупно и разбор обозначений."""

    type: Literal["formula"]
    formula: str = field(doc="Формула целиком: LaTeX в $…$ или юникодом")
    heading: Optional[str] = field(default=None, doc="Что это за формула")
    text: Optional[str] = field(default=None, doc="Строка под формулой: что она говорит")
    terms: Optional[list[TermSpec]] = field(
        default=None, min_items=1, doc="Обозначения: по паре «символ — расшифровка»"
    )
    id: Optional[str] = None


def emit(model: FormulaSpec, scope: str) -> dict[str, object]:
    data: dict[str, object] = {"type": "formula", "formula": _display(runs(model.formula))}
    if model.heading is not None:
        data["heading"] = runs(model.heading)
    if model.text is not None:
        data["text"] = runs(model.text)
    if model.terms is not None:
        data["terms"] = [
            {"symbol": runs(term.symbol), "meaning": runs(term.meaning)} for term in model.terms
        ]
    return data


def _display(parsed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The formula's own math goes out in display form.

    The author writes `$…$` here as everywhere else — the difference between
    a formula inside a sentence and a formula that *is* the slide belongs to
    the kind, not to how many dollar signs were typed.
    """
    return [{**run, "display": True} if "math" in run else run for run in parsed]


def build(model: FormulaSpec) -> Slide:
    """The formula large, what it says under it, and the symbols spelled out.

    The formula is set in display form here as it is for the player, and for
    the same reason: `$…$` is how an author writes maths everywhere, and
    whether this one *is* the slide is a property of the kind, not of how
    many dollar signs were typed.

    The glossary is two places rather than one — symbols right-aligned in a
    column of their own, meanings left-aligned in the next. A single
    placeholder with «$S$ — путь» in every line would leave the dashes on a
    ragged edge, and the whole point of a glossary is that the eye runs down
    one column.
    """
    layout = layouts.FORMULA
    notes: list[str] = []
    shapes = (
        layout.places[0].on_slide(2, [paragraph(model.heading)])
        if model.heading is not None
        else layouts.kicker(KICKER)
    )
    shapes += layout.places[1].on_slide(3, [runs_paragraph(_display_math(model.formula), notes=notes)])
    if model.text is not None:
        shapes += layout.places[2].on_slide(4, [paragraph(model.text, notes=notes)])
    if model.terms:
        shapes += layout.places[3].on_slide(
            5, [paragraph(term.symbol, notes=notes) for term in model.terms]
        )
        shapes += layout.places[4].on_slide(
            6, [paragraph(term.meaning, notes=notes) for term in model.terms]
        )
    return Slide(layout.name, shapes, tuple(notes))


def _display_math(formula: str) -> list[object]:
    """The author's line with its maths marked as display.

    `m:oMathPara` is what makes a fraction stand at full height instead of
    being squeezed into a line — the OMML counterpart of what the player
    asked KaTeX for.
    """
    return [
        Math(piece.latex, display=True) if isinstance(piece, Math) else piece
        for piece in parse_inline(formula)
    ]


register(
    tag="formula",
    title="Формула",
    model=FormulaSpec,
    emit=emit,
    build=build,
    order=40,
    module=__name__,
)
