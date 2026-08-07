"""Fill in the blanks, carried by a sentence."""

from __future__ import annotations

import re
from typing import Literal, Optional

from physics_svg.document.answers import Answer, Inline
from physics_svg.document.domain import Domain
from physics_svg.document.layout import Bank, Block, Gap, Para, Stack
from physics_svg.document.layout import Inline as InlinePart
from physics_svg.document.questions.registry import register
from physics_svg.document.strings import t
from physics_svg.inline import math_spans, parse_inline
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
        # A gap inside `$…$` splits the formula in two, and neither half is
        # LaTeX any more: the sheet gets a line of source instead of a
        # formula. Refused with a path to the block rather than printed.
        inside = _gap_inside_math(self.template)
        if inside is not None:
            raise Invalid(
                f"пропуск '___{inside}___' стоит внутри формулы $…$ — формула так не "
                "соберётся; вынеси пропуск за формулу или запиши выражение "
                "обычным текстом (см. references/symbols.md)",
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


def _gap_inside_math(template: str) -> Optional[str]:
    """The name of the first gap that fell inside a formula, if any."""
    spans = math_spans(template)
    for found in BLANK_RE.finditer(template):
        if any(start <= found.start() and found.end() <= end for start, end in spans):
            return found.group(1)
    return None


def body(model: FillTextSpec) -> Block:
    # The template's own underscores are not ruling here: in this kind a place
    # to write is a named gap, and bare underscores are literal text.
    pieces: list[InlinePart] = []
    last = 0
    for found in BLANK_RE.finditer(model.template):
        pieces.extend(parse_inline(model.template[last : found.start()]))
        pieces.append(Gap())
        last = found.end()
    pieces.extend(parse_inline(model.template[last:]))
    text = Para(tuple(pieces))
    if not model.bank:
        return text
    bank = Bank(t("bank_label"), tuple(parse_inline(word) for word in model.bank))
    return Stack((bank, text))


def answer(model: FillTextSpec) -> Answer:
    # Values in the order the gaps appear in the sentence.
    values = [model.blanks[found.group(1)] for found in BLANK_RE.finditer(model.template)]
    return Inline(parse_inline("; ".join(values)))


register(
    tag="fill_text",
    title="Пропуски в тексте",
    model=FillTextSpec,
    body=body,
    answer=answer,
    order=70,
    module=__name__,
)
