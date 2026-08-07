"""Multiple choice — one correct option or several."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.domain import Domain
from physics_svg.document.layout import Block, Bullets, Hint, Item, Run, Stack
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import LETTERS, t
from physics_svg.inline import parse_inline
from physics_svg.schema import Invalid, field, spec


@spec
class OptionSpec:
    """Вариант ответа."""

    text: str
    correct: bool = False


@spec
class ChoiceSpec:
    """Выбор одного или нескольких вариантов."""

    type: Literal["choice"]
    options: list[OptionSpec] = field(min_items=1, doc="Варианты; правильность — инлайн")
    select: Literal["single", "multiple"] = "single"
    id: Optional[str] = None
    explanation: Optional[str] = None

    @property
    def domain(self) -> Domain:
        """The options themselves: printed as а), б), в), the wrong ones are
        the distractors."""
        return Domain([option.text for option in self.options], "options", lettered=True)

    def check(self) -> None:
        self.domain.check()
        correct = sum(1 for option in self.options if option.correct)
        if self.select == "single" and correct != 1:
            raise Invalid(
                f"при select='single' правильный вариант должен быть ровно один, "
                f"получено {correct}",
                field="options",
            )
        if self.select == "multiple" and correct == 0:
            raise Invalid(
                "при select='multiple' нужен хотя бы один правильный вариант", field="options"
            )


def body(model: ChoiceSpec) -> Block:
    """Correctness is not marked in any way here — it is printed as a letter
    in the answers section."""
    items: tuple[Item, ...] = tuple(parse_inline(option.text) for option in model.options)
    options = Bullets(items, marker="letter")
    if model.select == "multiple":
        # Without the hint a student cannot tell `multiple` from `single`:
        # both render as the same list of options.
        return Stack((Hint((Run(t("choice_multiple_hint")),)), options))
    return options


def answer(model: ChoiceSpec) -> Answer:
    # The same а)/б) actually printed as list markers: one source of letters.
    letters = [LETTERS[i] for i, option in enumerate(model.options) if option.correct]
    return Inline((Run(", ".join(letters)),))


register(
    tag="choice",
    title="Выбор варианта",
    model=ChoiceSpec,
    body=body,
    answer=answer,
    order=20,
    module=__name__,
)
