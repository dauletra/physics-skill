"""The vocabulary a student takes an answer from.

Four kinds offer the student a closed set to choose from: `choice` its
options, `match` its right column, `classify` its groups, `fill_text` and
`fill_table` their word bank. The author writes the field natural to the kind
— `options`, `right`, `categories`, `bank` — and the kind projects it onto a
`Domain`, the way `plot` projects its axes onto a `GraphSpec`. Everything that
is the same for all of them happens here, once:

* the offered values are distinct;
* an inline answer really names one of them;
* a vocabulary printed as `а)`, `б)`, `в)` fits the alphabet.

And the part a teacher notices: **a value nothing points at is a distractor**.
An extra unit in the right column, an extra word in the bank, a group nobody
belongs to — one idea with one name, not a separate trick per kind. Which
values are offered and how they are printed stays with the kind; what it means
to be a vocabulary lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from physics_svg.document.strings import LETTERS
from physics_svg.schema import Invalid


@dataclass(frozen=True)
class Domain:
    """A closed set of values an answer may name.

    `keys` are what an answer names — an explicit id for `match`, the group's
    own name for `classify`, the word itself for a bank. `field_name` is the
    author's field, so both the message and the error path point at the JSON
    they actually wrote.
    """

    keys: list[str]
    field_name: str
    #: Printed as `а)`, `б)`, `в)` — so the set cannot outgrow the alphabet.
    lettered: bool = False

    def check(self) -> None:
        """Invariants of the vocabulary itself."""
        if len(set(self.keys)) != len(self.keys):
            raise Invalid(
                f"значения должны быть уникальны, получено {self.keys}", field=self.field_name
            )
        if self.lettered and len(self.keys) > len(LETTERS):
            raise Invalid(
                f"не больше {len(LETTERS)} вариантов — они печатаются буквами, "
                f"получено {len(self.keys)}",
                field=self.field_name,
            )

    def check_member(
        self, value: str, *, field: str, index: Optional[int] = None, attr: str = ""
    ) -> None:
        """One inline answer belongs to the vocabulary.

        `field`/`index`/`attr` spell out where the offending value sits, so the
        author reads «items[2].category = 'Оптика' нет среди categories […]»
        rather than a complaint about the question as a whole.
        """
        if value in self.keys:
            return
        where = field if index is None else f"{field}[{index}]"
        if attr:
            where = f"{where}.{attr}"
        raise Invalid(
            f"{where} = '{value}' нет среди {self.field_name} {self.keys}", field=field
        )
