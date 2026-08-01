"""Fixtures built from the question registry — and from its documentation.

The examples come from the reference fragment through `QuestionType`: the
task a teacher (or the model) is told to write is the task the suite renders,
so a documented example cannot rot into something the validator rejects.
Finding them lives in the registry, not here — the site renders the same
examples and must not reimplement the extraction.

Not a `conftest.py` on purpose — see tests/visuals/library.py.
"""

from __future__ import annotations

from typing import Any, Iterator, NamedTuple

import pytest

from physics_svg.document.questions import QuestionType, load_all


class Kind(NamedTuple):
    type: QuestionType

    @property
    def tag(self) -> str:
        return self.type.tag

    @property
    def task(self) -> dict[str, Any]:
        """The canonical documented task, whole."""
        return self.type.example

    @property
    def tasks(self) -> list[dict[str, Any]]:
        """Every documented task of this kind — `choice` has two."""
        return self.type.examples

    @property
    def example(self) -> dict[str, Any]:
        """The question payload inside the canonical task."""
        return self.type.question_in(self.task)

    @property
    def statement(self) -> str:
        """The wording the example puts beside its question."""
        texts = [b["body"] for b in self.task["blocks"] if b.get("type") == "text"]
        assert texts, f"в примере '{self.tag}' нет блока 'text' с условием"
        return str(texts[0])

    def task_with(self, payload: dict[str, Any]) -> dict[str, Any]:
        """The documented task with its question replaced — used by the fuzz.

        Only the task's own blocks: an example that hides its question inside
        a `part` would otherwise be fuzzed without the payload ever reaching
        the renderer, and the escaping tests would pass on nothing.
        """
        blocks = [
            payload if block.get("type") == self.tag else block
            for block in self.task["blocks"]
        ]
        assert payload in blocks, f"вопрос '{self.tag}' не на верхнем уровне примера"
        return {**self.task, "blocks": blocks}


def all_kinds() -> Iterator[Kind]:
    for entry in load_all().values():
        yield Kind(entry)


KINDS = list(all_kinds())


#: Ready-made parametrisation over every registered question kind.
EACH_KIND = pytest.mark.parametrize("kind", KINDS, ids=[k.tag for k in KINDS])
