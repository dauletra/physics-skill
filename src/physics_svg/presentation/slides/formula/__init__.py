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

from physics_svg.presentation.emit import runs
from physics_svg.presentation.slides.registry import register
from physics_svg.schema import field, spec


@spec
class TermSpec:
    """Обозначение из формулы и его расшифровка."""

    symbol: str = field(doc="Обозначение как в формуле: υ₀, a, t")
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


register(
    tag="formula",
    title="Формула",
    model=FormulaSpec,
    emit=emit,
    order=40,
    module=__name__,
)
