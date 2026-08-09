"""The layouts a lesson is built from — one per kind of slide.

This is where the player's stylesheet lands. `.s-head`, the centred title,
the dark stage divider, the one horizon every slide's heading stands on:
each was a CSS rule and each is now a layout, because that is where
PowerPoint keeps such decisions.

A layout is added by adding an entry to `LAYOUTS`. Everything else — the
master's list, the parts of the package, the relationships — is derived from
it, the same way the rest of the project derives from its registries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from physics_svg.ooxml import el
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.shape import Place, rule
from physics_svg.presentation.pptx.slide import NS, shape_tree

#: The slide in points, and the box the content lives in.
WIDTH = design.SLIDE_WIDTH / design.emu(1)
HEIGHT = design.SLIDE_HEIGHT / design.emu(1)
CONTENT_WIDTH = WIDTH - 2 * design.PAD_X

#: The heading band: where a slide's heading sits and where its rule is.
#: Fixed for every kind, so that the class's eye does not hunt for it when
#: the slide changes (docs/slide-design.md §6.2).
HEAD_TOP = design.PAD_Y
HEAD_HEIGHT = design.HEADING * 1.5
RULE_Y = HEAD_TOP + HEAD_HEIGHT + design.cqh(1.0)
BODY_TOP = RULE_Y + design.cqh(2.5)
BODY_HEIGHT = HEIGHT - BODY_TOP - design.PAD_Y


@dataclass(frozen=True)
class Layout:
    """One layout: its places, and the ornament drawn behind them."""

    #: The tag a slide kind asks for it by.
    name: str
    #: What PowerPoint shows in «Образец слайдов».
    title: str
    places: tuple[Place, ...]
    #: `p:sldLayout type` — PowerPoint uses it to pick an icon and to guess
    #: what «Создать слайд» should offer.
    kind: str = "obj"
    #: Fill behind everything; `None` inherits the master's paper.
    background: str | None = None
    #: Decoration that is not a place: the rule under the heading.
    ornament: str = ""

    def xml(self) -> str:
        shapes = "".join(
            place.on_layout(index + 2, prompt=place.name)
            for index, place in enumerate(self.places)
        )
        content = self._background() + shape_tree(shapes + self.ornament)
        return el(
            "p:sldLayout",
            {**NS, "type": self.kind, "preserve": "1"},
            el("p:cSld", {"name": self.title}, content)
            + el("p:clrMapOvr", children=el("a:masterClrMapping")),
        )

    def _background(self) -> str:
        if self.background is None:
            return ""
        return el(
            "p:bg",
            children=el(
                "p:bgPr",
                children=el("a:solidFill", children=el("a:srgbClr", {"val": self.background}))
                + el("a:effectLst"),
            ),
        )


#: The title of the lesson. Centred vertically and left-aligned: centred
#: Russian text of unpredictable length reads worse than a firm left edge,
#: and the vertical centring is what the player did for this kind alone.
TITLE = Layout(
    name="title",
    title="Титул",
    kind="title",
    places=(
        Place(
            name="Название урока",
            kind="ctrTitle",
            box=(design.PAD_X, design.cqh(30.0), CONTENT_WIDTH, design.HERO * 2.4),
            size=design.HERO,
            bold=True,
            anchor="b",
            leading=1.1,
        ),
        Place(
            name="Класс и тема",
            kind="subTitle",
            idx=1,
            box=(design.PAD_X, design.cqh(64.0), CONTENT_WIDTH, design.LEAD * 2.0),
            size=design.LEAD,
            colour=design.INK_SOFT,
        ),
    ),
)

#: The stage divider. Dark, so the class sees that one part of the lesson
#: has ended — and dark blue-graphite rather than black, because a black
#: fill on a lit panel flashes between two white slides.
SECTION = Layout(
    name="section",
    title="Этап урока",
    kind="secHead",
    background=design.PANEL,
    places=(
        Place(
            name="Название этапа",
            kind="title",
            box=(design.PAD_X, design.cqh(35.0), CONTENT_WIDTH, design.DISPLAY * 2.2),
            size=design.DISPLAY,
            colour=design.PAPER,
            bold=True,
            anchor="ctr",
            leading=1.15,
        ),
    ),
)

#: The workhorse: a heading and whatever explains it.
CONTENT = Layout(
    name="content",
    title="Объяснение",
    places=(
        Place(
            name="Заголовок",
            kind="title",
            box=(design.PAD_X, HEAD_TOP, CONTENT_WIDTH, HEAD_HEIGHT),
            size=design.HEADING,
            bold=True,
            anchor="b",
        ),
        Place(
            name="Содержание",
            kind="body",
            idx=1,
            box=(design.PAD_X, BODY_TOP, CONTENT_WIDTH, BODY_HEIGHT),
            size=design.TEXT,
            leading=design.LEADING,
        ),
    ),
    ornament=rule(RULE_Y),
)

#: Kept because PowerPoint offers it in «Создать слайд» and a teacher will
#: reach for it; nothing the skill generates uses it.
BLANK = Layout(name="blank", title="Пустой", kind="blank", places=())

LAYOUTS: tuple[Layout, ...] = (TITLE, SECTION, CONTENT, BLANK)


def layout_index(name: str) -> int:
    """Which layout part a slide kind stands on, one-based — the number in
    `slideLayoutN.xml`."""
    for index, layout in enumerate(LAYOUTS):
        if layout.name == name:
            return index + 1
    raise KeyError(f"нет макета {name!r}; известные: {[item.name for item in LAYOUTS]}")


def places(name: str) -> Sequence[Place]:
    return LAYOUTS[layout_index(name) - 1].places
