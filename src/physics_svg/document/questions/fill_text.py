"""Fill in the blanks, carried by a sentence."""

from __future__ import annotations

import re
from typing import Literal, Optional

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.domain import Domain
from physics_svg.document.html import bank_list, blank_cell
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import t
from physics_svg.draw import esc
from physics_svg.schema import Invalid, field, spec

#: A placeholder in the template: `___имя___`. The name is the key in
#: `blanks`, so reordering the sentence never renumbers anything.
BLANK_RE = re.compile(r"___(\w+)___")


@spec
class FillTextSpec:
    """Текст с пропусками."""

    type: Literal["fill_text"]
    template: str = field(doc="Текст с пропусками вида ___имя___")
    blanks: dict[str, str] = field(doc="Имя пропуска -> правильное значение")
    id: Optional[str] = None
    explanation: Optional[str] = None
    bank: Optional[list[str]] = field(default=None, doc="Слова для выбора, если нужен банк")

    @property
    def domain(self) -> Optional[Domain]:
        """The word bank, when there is one: printed above the text, extra
        words are the distractors."""
        return None if self.bank is None else Domain(self.bank, "bank")

    def check(self) -> None:
        placeholders = set(BLANK_RE.findall(self.template))
        # `_` is a word character, so a long run of underscores would otherwise
        # parse as a gap named `_` — and the author meant a ruled space, which
        # is a `text` block's business.
        underscore_only = sorted(name for name in placeholders if not name.strip("_"))
        if underscore_only:
            raise Invalid(
                "имя пропуска не может состоять из подчёркиваний; место для записи "
                "без ответа — подчёркивания в блоке 'text'",
                field="template",
            )
        if not placeholders:
            # A template with no gaps is not a question: the body prints plain
            # text and the answer line comes out empty. That is a `text` block.
            raise Invalid(
                "в шаблоне нет пропусков ___имя___ — это обычный блок 'text', а не fill_text",
                field="template",
            )
        if placeholders != set(self.blanks):
            raise Invalid(
                f"пропуски шаблона {sorted(placeholders)} не совпадают с ключами blanks "
                f"{sorted(self.blanks)}",
                field="blanks",
            )
        # A bank that misses a correct word makes the task unsolvable, and
        # nothing on the sheet gives that away.
        if self.domain is not None:
            self.domain.check()
            for name, value in self.blanks.items():
                self.domain.check_member(value, field="blanks", attr=name)


def body(model: FillTextSpec) -> str:
    pieces: list[str] = []
    last = 0
    for found in BLANK_RE.finditer(model.template):
        pieces.append(esc(model.template[last : found.start()]))
        pieces.append(blank_cell())
        last = found.end()
    pieces.append(esc(model.template[last:]))
    text = f'<p>{"".join(pieces)}</p>'
    return bank_list(model.bank, t("bank_label")) + text if model.bank else text


def answer(model: FillTextSpec) -> Answer:
    # Values in the order the gaps appear in the sentence.
    values = [model.blanks[found.group(1)] for found in BLANK_RE.finditer(model.template)]
    return Inline(esc("; ".join(values)))


register(
    tag="fill_text",
    title="Пропуски в тексте",
    model=FillTextSpec,
    body=body,
    answer=answer,
    order=70,
    module=__name__,
)
