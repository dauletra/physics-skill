"""What appears on a click, and the `p:timing` tree that makes it happen.

A slide with a worked example must not show its solution before the class has
thought about it, and a slide with a task must not show its answer. The player
did that with a spoiler plate and a fragment list; PowerPoint does it with
animation, and there is no third way — a deck has no code of ours running in
it (docs/pptx.md §6.2).

**This is the most fragile XML the deck writes.** Everything else fails
locally: a bad fill is a wrong colour, a bad box is a shape in the wrong
place. `p:timing` fails globally — PowerPoint refuses the slide show, not the
effect. Three consequences run through this module:

* the tree is written the way PowerPoint writes it, nesting and all, rather
  than the shortest way that looks equivalent;
* a slide with nothing to reveal gets **no `p:timing` element at all**, so
  every slide that does not animate is untouched by any of this;
* what a test can hold, it holds — the ids inside the tree are unique and
  every shape the tree points at exists on the slide. A dangling `spid` is
  the classic way to lose a show, and it is checkable.

**The order is the whole design.** Clicks form one queue: there is no key in
PowerPoint that skips animations, so a step of a solution and the revealing of
an answer are the same gesture (§4). Therefore the answer is always **last** —
a teacher who clicks through the steps must not be able to reach the answer
before meaning to.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from physics_svg.ooxml import el

#: «Появление» — the simplest entrance there is. Chosen for portability, not
#: for taste: a plain appearance is the one effect Google Slides and
#: LibreOffice have a chance of playing, and anything with motion in it would
#: be a distraction on a lesson slide anyway.
_APPEAR = {"presetID": 1, "presetClass": "entr", "presetSubtype": 0}


@dataclass(frozen=True)
class Reveal:
    """One thing that waits for a click.

    `paragraphs` empty means the whole shape appears at once — an answer,
    which is one line and one decision. Naming paragraphs animates them one
    by one inside a shape that stays where it is: the steps of a worked
    example are one placeholder, because they are one numbered list and
    PowerPoint numbers it.
    """

    #: The shape's `p:cNvPr` id on this slide.
    shape: int
    paragraphs: tuple[int, ...] = ()


def timing(reveals: Sequence[Reveal]) -> str:
    """`p:timing` for a slide, or nothing at all when nothing is revealed."""
    clicks: list[tuple[int, int | None]] = [
        (reveal.shape, index)
        for reveal in reveals
        for index in (reveal.paragraphs if reveal.paragraphs else (None,))
    ]
    if not clicks:
        return ""
    body = ""
    # Ids 1 and 2 are the root and the main sequence; every click takes four.
    for number, (shape, paragraph) in enumerate(clicks):
        body += _click(3 + number * 4, shape, paragraph)
    return el(
        "p:timing",
        children=el("p:tnLst", children=_root(_sequence(body))) + _builds(reveals),
    )


def _root(sequence: str) -> str:
    return el(
        "p:par",
        children=el(
            "p:cTn",
            {"id": 1, "dur": "indefinite", "restart": "never", "nodeType": "tmRoot"},
            el("p:childTnLst", children=sequence),
        ),
    )


def _sequence(clicks: str) -> str:
    """The main sequence, with the two conditions that make it a *sequence*.

    `prevCondLst` and `nextCondLst` are what bind a click on the slide to the
    next effect. Without them the effects exist and nothing ever starts them,
    which looks exactly like an animation that «did not work».
    """
    target = el("p:tgtEl", children=el("p:sldTgt"))
    return el(
        "p:seq",
        {"concurrent": 1, "nextAc": "seek"},
        el(
            "p:cTn",
            {"id": 2, "dur": "indefinite", "nodeType": "mainSeq"},
            el("p:childTnLst", children=clicks),
        )
        + el(
            "p:prevCondLst",
            children=el("p:cond", {"evt": "onPrev", "delay": 0}, target),
        )
        + el(
            "p:nextCondLst",
            children=el("p:cond", {"evt": "onNext", "delay": 0}, target),
        ),
    )


def _click(first_id: int, shape: int, paragraph: int | None) -> str:
    """One click: three nested `p:par` and the behaviour inside them.

    The nesting is not ceremony. The outer node waits for the click
    (`delay="indefinite"`), the middle one groups what that click starts, and
    the inner one is the effect itself. PowerPoint writes exactly this, and a
    flattened version of it is where «the show will not start» comes from.
    """
    effect = el(
        "p:par",
        children=el(
            "p:cTn",
            {"id": first_id + 2, **_APPEAR, "fill": "hold", "nodeType": "clickEffect"},
            _at_once() + el("p:childTnLst", children=_appear(first_id + 3, shape, paragraph)),
        ),
    )
    grouped = el(
        "p:par",
        children=el(
            "p:cTn",
            {"id": first_id + 1, "fill": "hold"},
            _at_once() + el("p:childTnLst", children=effect),
        ),
    )
    return el(
        "p:par",
        children=el(
            "p:cTn",
            {"id": first_id, "fill": "hold"},
            el("p:stCondLst", children=el("p:cond", {"delay": "indefinite"}))
            + el("p:childTnLst", children=grouped),
        ),
    )


def _at_once() -> str:
    return el("p:stCondLst", children=el("p:cond", {"delay": 0}))


def _appear(node_id: int, shape: int, paragraph: int | None) -> str:
    """Making one thing visible — the whole of «Появление».

    An entrance effect is what tells PowerPoint the thing starts hidden; the
    slide itself says nothing about visibility, which is why a deck opened
    somewhere that ignores animation shows everything rather than nothing.
    """
    return el(
        "p:set",
        children=el(
            "p:cBhvr",
            children=el(
                "p:cTn", {"id": node_id, "dur": 1, "fill": "hold"}, _at_once()
            )
            + el("p:tgtEl", children=_target(shape, paragraph))
            + el(
                "p:attrNameLst",
                children=el("p:attrName", children="style.visibility"),
            ),
        )
        + el("p:to", children=el("p:strVal", {"val": "visible"})),
    )


def _target(shape: int, paragraph: int | None) -> str:
    if paragraph is None:
        return el("p:spTgt", {"spid": shape})
    return el(
        "p:spTgt",
        {"spid": shape},
        el("p:txEl", children=el("p:pRg", {"st": paragraph, "end": paragraph})),
    )


def _builds(reveals: Sequence[Reveal]) -> str:
    """`p:bldLst` — how the animation pane describes what was done.

    Only shapes animated paragraph by paragraph appear here: it is the record
    of «build by paragraph», and a shape that appears whole has nothing to
    declare.
    """
    entries = "".join(
        el("p:bldP", {"spid": reveal.shape, "grpId": 0, "build": "p"})
        for reveal in reveals
        if reveal.paragraphs
    )
    return el("p:bldLst", children=entries) if entries else ""
