"""True or false — a series of statements to judge."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.inline import parse_inline
from physics_svg.document.layout import Bullets, Item, Run, Statement, Verdict
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import LETTERS, t
from physics_svg.schema import Invalid, field, spec


@spec
class StatementSpec:
    """Утверждение с правильным вердиктом инлайн."""

    text: str
    answer: bool


@spec
class TrueFalseSpec:
    """Верно или неверно."""

    type: Literal["true_false"]
    statements: list[StatementSpec] = field(min_items=1)
    id: Optional[str] = None
    explanation: Optional[str] = None

    def check(self) -> None:
        if len(self.statements) > len(LETTERS):
            raise Invalid(
                f"не больше {len(LETTERS)} утверждений — они печатаются буквами, "
                f"получено {len(self.statements)}",
                field="statements",
            )


def body(model: TrueFalseSpec) -> Bullets:
    rows: tuple[Item, ...] = tuple(
        Statement(parse_inline(statement.text), Verdict())
        for statement in model.statements
    )
    # Lettered, so a verdict has something to name — and lettered rather than
    # numbered because a sheet already enumerates with а)/б): subtasks, options.
    return Bullets(rows, marker="letter")


def answer(model: TrueFalseSpec) -> Answer:
    # One line: a verdict is two words, and six of them still read as a line.
    # The same а)/б) actually printed as list markers: one source of letters.
    verdicts = [
        f"{LETTERS[i]} — {t('true_label') if statement.answer else t('false_label')}"
        for i, statement in enumerate(model.statements)
    ]
    return Inline((Run(", ".join(verdicts)),))


register(
    tag="true_false",
    title="Верно/неверно",
    model=TrueFalseSpec,
    body=body,
    answer=answer,
    order=30,
    module=__name__,
)
