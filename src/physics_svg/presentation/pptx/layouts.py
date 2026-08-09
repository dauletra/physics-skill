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

from dataclasses import dataclass, replace
from typing import Sequence

from physics_svg.ooxml import el, escape
from physics_svg.presentation.pptx import design
from physics_svg.presentation.pptx.shape import Place, plain_shape, rule
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
    #: Where an illustration goes, in points. Not a placeholder: PowerPoint
    #: has one for pictures, and a group of native shapes is not a picture.
    #: The box is declared here anyway so that the layout, and not the slide
    #: kind, stays the one place that knows where things sit.
    picture: tuple[float, float, float, float] | None = None

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

#: Text beside the illustration. The proportion is the player's, and it was
#: measured rather than guessed: 1.2 to 1 in favour of the text, because at
#: the reverse the explanation dropped below the size a class reads at while
#: the picture gained percentages of width it could not use
#: (docs/slide-design.md §6.3).
_GAP = design.cqh(3.0)
_TEXT_COLUMN = (CONTENT_WIDTH - _GAP) * 1.2 / 2.2
_PICTURE_COLUMN = (CONTENT_WIDTH - _GAP) / 2.2

CONTENT_SPLIT = Layout(
    name="content_split",
    title="Объяснение с иллюстрацией",
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
            box=(design.PAD_X, BODY_TOP, _TEXT_COLUMN, BODY_HEIGHT),
            size=design.TEXT,
            leading=design.LEADING,
        ),
    ),
    ornament=rule(RULE_Y),
    picture=(
        design.PAD_X + _TEXT_COLUMN + _GAP,
        BODY_TOP,
        _PICTURE_COLUMN,
        BODY_HEIGHT,
    ),
)

#: Text above the illustration, the illustration across the frame. Where a
#: picture cannot be read beside the text this is where it goes: measured,
#: eleven specs of the library came out at 16–19 pt in the narrow column
#: against a threshold of 19, and every one of them clears it here.
_STACK_TEXT_HEIGHT = design.TEXT * design.LEADING * 2.4
_STACK_PICTURE_TOP = BODY_TOP + _STACK_TEXT_HEIGHT + design.cqh(1.5)

CONTENT_STACK = Layout(
    name="content_stack",
    title="Объяснение над иллюстрацией",
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
            box=(design.PAD_X, BODY_TOP, CONTENT_WIDTH, _STACK_TEXT_HEIGHT),
            size=design.TEXT,
            leading=design.LEADING,
        ),
    ),
    ornament=rule(RULE_Y),
    picture=(
        design.PAD_X,
        _STACK_PICTURE_TOP,
        CONTENT_WIDTH,
        HEIGHT - _STACK_PICTURE_TOP - design.PAD_Y,
    ),
)


#: Nothing but the picture: the slide whose whole point is what is drawn on
#: it. The illustration gets the width of the frame, which is the only way a
#: graph reaches the size the back row reads it at.
CONTENT_FIGURE = Layout(
    name="content_figure",
    title="Иллюстрация",
    places=(
        Place(
            name="Заголовок",
            kind="title",
            box=(design.PAD_X, HEAD_TOP, CONTENT_WIDTH, HEAD_HEIGHT),
            size=design.HEADING,
            bold=True,
            anchor="b",
        ),
    ),
    ornament=rule(RULE_Y),
    picture=(design.PAD_X, BODY_TOP, CONTENT_WIDTH, BODY_HEIGHT),
)


def kicker(text: str, *, number: int = 91) -> str:
    """The word that names the genre, standing where a heading would.

    Ornament rather than a place: the word belongs to the kind, not to the
    slide — every task says «Задача», and no author gets to retype it. A kind
    without a heading still needs something on the horizon every other slide's
    heading stands on ([slide-design.md](slide-design.md) §6.1), and a kind
    whose heading already names the genre gets no kicker at all: that would be
    the same word twice.

    Set in the accent, in caps, letterspaced. At 16 pt it is the smallest
    thing on the slide, and the class has to read it as a label rather than as
    the first words of the text.
    """
    run = el(
        "a:r",
        children=el(
            "a:rPr",
            {"lang": "ru-RU", "sz": design.sz(design.TINY), "b": 1, "cap": "all", "spc": 130},
            el("a:solidFill", children=el("a:srgbClr", {"val": design.ACCENT}))
            + el("a:latin", {"typeface": design.FONT}),
        )
        + el("a:t", children=escape(text)),
    )
    box = (design.PAD_X, HEAD_TOP, CONTENT_WIDTH, HEAD_HEIGHT)
    return plain_shape(number, "Жанр", box, el("a:p", children=run), anchor="b")


#: The task slide. Its shape is the player's, top to bottom: the statement,
#: then the picture if there is one, then the answer.
#:
#: The answer keeps a band of its own at the foot of the frame rather than
#: following the text. Two reasons, and the second is the one that matters:
#: the class always looks for it in the same place, and the picture above it
#: therefore has a height that is known before the slide is built — which is
#: what `reads_in` needs to choose where the picture goes.
#:
#: One line and a half of it. An answer to a task at the board is «12 с», not
#: a paragraph; a longer one is shrunk by `normAutofit` rather than given room
#: that the picture would have to pay for.
_ANSWER_HEIGHT = design.TEXT * design.LEADING * 1.4
_ANSWER_TOP = HEIGHT - design.PAD_Y - _ANSWER_HEIGHT
_TASK_GAP = design.cqh(1.5)
_TASK_BOTTOM = _ANSWER_TOP - _TASK_GAP

#: The statement is set a step above body text: it is the whole slide until
#: someone answers it, and the class reads it before anything else is on the
#: board.
_STATEMENT = Place(
    name="Условие",
    kind="title",
    box=(design.PAD_X, BODY_TOP, CONTENT_WIDTH, _TASK_BOTTOM - BODY_TOP),
    size=design.LEAD,
    leading=design.LEADING,
)
_ANSWER = Place(
    name="Ответ",
    kind="body",
    idx=1,
    box=(design.PAD_X, _ANSWER_TOP, CONTENT_WIDTH, _ANSWER_HEIGHT),
    size=design.TEXT,
    anchor="b",
)

TASK = Layout(
    name="task",
    title="Задача у доски",
    places=(_STATEMENT, _ANSWER),
    ornament=rule(RULE_Y) + kicker("Задача"),
)

TASK_SPLIT = Layout(
    name="task_split",
    title="Задача с иллюстрацией сбоку",
    places=(
        replace(
            _STATEMENT,
            box=(design.PAD_X, BODY_TOP, _TEXT_COLUMN, _TASK_BOTTOM - BODY_TOP),
        ),
        _ANSWER,
    ),
    ornament=rule(RULE_Y) + kicker("Задача"),
    picture=(
        design.PAD_X + _TEXT_COLUMN + _GAP,
        BODY_TOP,
        _PICTURE_COLUMN,
        _TASK_BOTTOM - BODY_TOP,
    ),
)

#: The statement over the picture. Two lines of it: a task read off a graph
#: says «найдите путь за первые 4 секунды» and hands the rest to the drawing.
_TASK_TEXT_HEIGHT = design.LEAD * design.LEADING * 2.0
_TASK_PICTURE_TOP = BODY_TOP + _TASK_TEXT_HEIGHT + _TASK_GAP

TASK_STACK = Layout(
    name="task_stack",
    title="Задача над иллюстрацией",
    places=(
        replace(
            _STATEMENT,
            box=(design.PAD_X, BODY_TOP, CONTENT_WIDTH, _TASK_TEXT_HEIGHT),
        ),
        _ANSWER,
    ),
    ornament=rule(RULE_Y) + kicker("Задача"),
    picture=(
        design.PAD_X,
        _TASK_PICTURE_TOP,
        CONTENT_WIDTH,
        _TASK_BOTTOM - _TASK_PICTURE_TOP,
    ),
)


#: Kept because PowerPoint offers it in «Создать слайд» and a teacher will
#: reach for it; nothing the skill generates uses it.
BLANK = Layout(name="blank", title="Пустой", kind="blank", places=())

LAYOUTS: tuple[Layout, ...] = (
    TITLE,
    SECTION,
    CONTENT,
    CONTENT_SPLIT,
    CONTENT_STACK,
    CONTENT_FIGURE,
    TASK,
    TASK_SPLIT,
    TASK_STACK,
    BLANK,
)


def layout_index(name: str) -> int:
    """Which layout part a slide kind stands on, one-based — the number in
    `slideLayoutN.xml`."""
    for index, layout in enumerate(LAYOUTS):
        if layout.name == name:
            return index + 1
    raise KeyError(f"нет макета {name!r}; известные: {[item.name for item in LAYOUTS]}")


def places(name: str) -> Sequence[Place]:
    return LAYOUTS[layout_index(name) - 1].places


def reads_in(picture: tuple[float, float, float, float], model: object) -> bool:
    """Would the picture's smallest label be legible in this box?

    The one measurement the deck backend can still make. The player laid a
    slide out and looked at the result; here the picture is drawn, its
    frame and its smallest label are known, and fitting it into a rectangle
    is arithmetic. Everything else about the slide is guessed — this is not.
    """
    from physics_svg.visuals import label_metrics

    size, width, height = label_metrics(model)
    if not size:  # ruled paper carries no labels; any box will do
        return True
    _, _, box_width, box_height = picture
    return size * min(box_width / width, box_height / height) >= design.SMALL
