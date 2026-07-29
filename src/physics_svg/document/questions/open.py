"""Open question — a free-form answer."""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.document.questions.registry import register
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec


@spec
class OpenSpec:
    """Открытый вопрос: ответ свободной формы.

    Payload — только сам ответ: условие живёт соседним `text`-блоком, а место
    под ответ — соседним `paper`/`answer_line`.
    """

    type: Literal["open"]
    answer: Optional[str] = field(default=None, doc="Правильный ответ; без него — устный вопрос")
    id: Optional[str] = None
    explanation: Optional[str] = None

    def check(self) -> None:
        # An open question with no answer is legitimate (asked aloud, free
        # reasoning), but an explanation without one prints a comment in the
        # answers section about something that is not there.
        if self.explanation and not self.answer:
            raise Invalid(
                "пояснение без ответа: добавь 'answer' или убери 'explanation'",
                field="explanation",
            )


def body(model: OpenSpec) -> str:
    """Prints nothing at all.

    The statement is the neighbouring `text` and the place to write is the
    neighbouring `paper`/`answer_line`; it stays a question only so that its
    answer reaches the answers section.
    """
    return ""


def answer(model: OpenSpec) -> str:
    return esc(model.answer) if model.answer else ""


register(
    tag="open", title="Открытый вопрос", model=OpenSpec, body=body, answer=answer, module=__name__
)
