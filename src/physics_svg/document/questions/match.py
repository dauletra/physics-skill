"""Matching — pair each item on the left with one on the right."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.domain import Domain
from physics_svg.document.layout import Bullets, Facing, Item, Run
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import LETTERS
from physics_svg.inline import parse_inline
from physics_svg.schema import field, spec


@spec
class LeftSpec:
    """Пункт левого столбца."""

    text: str
    match: str = field(doc="id соответствующего пункта справа")


@spec
class RightSpec:
    """Пункт правого столбца (пула вариантов)."""

    id: str = field(min_length=1, doc="Устойчивый идентификатор, на него ссылается left")
    text: str


@spec
class MatchSpec:
    """Сопоставление двух столбцов."""

    type: Literal["match"]
    left: list[LeftSpec] = field(min_items=1)
    right: list[RightSpec] = field(min_items=1, doc="Пул вариантов; дистракторы допустимы")
    id: Optional[str] = None
    explanation: Optional[str] = None

    @property
    def domain(self) -> Domain:
        """The right column: printed as а), б), в), addressed by explicit id;
        an item nothing points at is a distractor."""
        return Domain([item.id for item in self.right], "right", lettered=True)

    def check(self) -> None:
        self.domain.check()
        for i, item in enumerate(self.left):
            self.domain.check_member(item.match, field="left", index=i, attr="match")


def body(model: MatchSpec) -> Facing:
    """Two columns. The link is by `id`, so shuffling either list breaks
    nothing — which is why the letters can be positional here."""
    left: tuple[Item, ...] = tuple(parse_inline(item.text) for item in model.left)
    right: tuple[Item, ...] = tuple(parse_inline(item.text) for item in model.right)
    return Facing((Bullets(left, marker="number"), Bullets(right, marker="letter")))


def answer(model: MatchSpec) -> Answer:
    letters = {item.id: LETTERS[i] for i, item in enumerate(model.right)}
    pairs = ", ".join(f"{i + 1}-{letters[item.match]}" for i, item in enumerate(model.left))
    return Inline((Run(pairs),))


register(
    tag="match",
    title="Сопоставление",
    model=MatchSpec,
    body=body,
    answer=answer,
    order=40,
    module=__name__,
)
