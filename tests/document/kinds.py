"""Fixtures built from the question registry — and from its documentation.

The example payload for each kind is **extracted from its reference
fragment**. That is deliberate: the JSON a teacher (or the model) is told to
write is the JSON the suite renders, so a documented example cannot rot into
something the validator rejects.

Not a `conftest.py` on purpose — see tests/visuals/library.py.
"""

from __future__ import annotations

import json
import re
from typing import Any, Iterator, NamedTuple

import pytest

from physics_svg.document.questions import QuestionType, load_all

JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)


class Kind(NamedTuple):
    type: QuestionType

    @property
    def tag(self) -> str:
        return self.type.tag

    @property
    def example(self) -> dict[str, Any]:
        """The first JSON block of the reference fragment."""
        text = self.type.doc.read_text(encoding="utf-8")
        match = JSON_BLOCK.search(text)
        assert match is not None, f"в {self.type.doc.name} нет примера в блоке ```json"
        return json.loads(match.group(1))

    def task(self, **extra: Any) -> dict[str, Any]:
        """A minimal valid task carrying this question."""
        return {
            "type": "task",
            "blocks": [{"type": "text", "body": "Условие задания."}, self.example],
            **extra,
        }


def all_kinds() -> Iterator[Kind]:
    for entry in load_all().values():
        yield Kind(entry)


KINDS = list(all_kinds())


#: Ready-made parametrisation over every registered question kind.
EACH_KIND = pytest.mark.parametrize("kind", KINDS, ids=[k.tag for k in KINDS])
