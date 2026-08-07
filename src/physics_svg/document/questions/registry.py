"""The registry of question types — the same shape as the visual registry.

A question type is one module declaring its spec, the **body** (what the
student sees — blank fields, unmarked options), the **answer** (its shape for
the section at the end), its place in the reading order, and a reference
fragment with worked examples. Registration happens on import, so adding a
pedagogical kind is adding a module.

Why two renderers and not a mode flag: a task body never contains answers at
all. The handout variant is the same document without the answers section,
not a second rendering of the same bodies — which is what makes it
impossible to leak an answer into a printed sheet by forgetting a flag.
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator

from physics_svg.document.answers import MaybeAnswer
from physics_svg.document.layout import Block

#: What the student sees, in the layout vocabulary — never markup: a kind
#: describes what to print, and a backend decides how it looks in HTML or in
#: Word. This is what makes a new kind work in both formats without writing
#: anything for either.
Renderer = Callable[[Any], Block]
#: The answers section is handed a shape, not finished layout — see
#: `document/answers.py` for why.
AnswerRenderer = Callable[[Any], MaybeAnswer]

#: The worked examples live in the fragment, in fenced JSON blocks.
_JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)


@dataclass(frozen=True)
class QuestionType:
    #: Value of the `type` field in JSON.
    tag: str
    #: Human name for the generated reference.
    title: str
    model: type
    #: What is printed in place of the task.
    body: Renderer
    #: The shape of the answer for the section at the end; `None` means "no
    #: answer" (an `open` question asked without one).
    answer: AnswerRenderer
    #: Place in everything a human reads — the site page, the reference
    #: index — by how often a kind is reached for, not by its latin tag.
    #: Multiples of ten, so a new kind slots in without renumbering.
    order: int
    directory: Path

    @property
    def doc(self) -> Path:
        """Reference fragment for the model: fields, invariants, JSON."""
        return self.directory / f"{self.tag}.md"

    @property
    def card(self) -> Path:
        """Gallery card for the teacher: what it is and what to ask for.

        Two audiences, two texts. The model needs field names; a teacher
        needs to know the kind exists and what phrase produces it.
        """
        return self.directory / f"{self.tag}.card.md"

    @property
    def examples(self) -> list[dict[str, Any]]:
        """The worked tasks from the fragment, in order of appearance.

        Each is a whole `task` — statement, question and the place to write —
        never a bare payload: a task is the smallest thing that validates and
        the smallest thing that prints. One source for three readers: the
        model reads them in the bundle, the suite renders them, the site
        shows them as sheets. So an example that stops working, or that
        stops showing what its card promises, fails the build.
        """
        blocks = _JSON_BLOCK.findall(self.doc.read_text(encoding="utf-8"))
        if not blocks:
            raise ValueError(f"в {self.doc.name} нет примера в блоке ```json")
        return [json.loads(block) for block in blocks]

    @property
    def example(self) -> dict[str, Any]:
        """The canonical task: the first example of the fragment."""
        return self.examples[0]

    def question_in(self, task: dict[str, Any]) -> dict[str, Any]:
        """This kind's question block inside one of its examples."""
        for block in _walk(task):
            if block.get("type") == self.tag:
                return block
        raise ValueError(f"в примере из {self.doc.name} нет вопроса '{self.tag}'")


def _walk(block: dict[str, Any]) -> Iterator[dict[str, Any]]:
    """Nested blocks of a raw task, containers included."""
    for inner in block.get("blocks", []):
        if isinstance(inner, dict):
            yield inner
            yield from _walk(inner)


_REGISTRY: dict[str, QuestionType] = {}
_LOADED = False


def register(
    *,
    tag: str,
    title: str,
    model: type,
    body: Renderer,
    answer: AnswerRenderer,
    order: int,
    module: str,
) -> None:
    if tag in _REGISTRY:
        raise RuntimeError(f"question type {tag!r} is already registered")
    taken = {entry.order: entry.tag for entry in _REGISTRY.values()}
    if order in taken:
        raise RuntimeError(f"order {order} is already taken by {taken[order]!r}")
    directory = Path(importlib.import_module(module).__file__ or "").parent
    _REGISTRY[tag] = QuestionType(tag, title, model, body, answer, order, directory)


def load_all() -> dict[str, QuestionType]:
    """Every registered kind, in the order a person meets them.

    Import order is whatever `pkgutil` walks, so the order is the declared
    one — the same on the site, in the reference index and in the union of
    allowed types.
    """
    global _LOADED
    if not _LOADED:
        package = importlib.import_module("physics_svg.document.questions")
        for info in pkgutil.iter_modules(package.__path__):
            if info.name != "registry":
                importlib.import_module(f"physics_svg.document.questions.{info.name}")
        _LOADED = True
    return dict(sorted(_REGISTRY.items(), key=lambda item: item[1].order))


def question_models() -> tuple[type, ...]:
    return tuple(entry.model for entry in load_all().values())


def is_question(model: object) -> bool:
    return isinstance(model, question_models())


def render_body(model: Any) -> Block:
    return load_all()[model.type].body(model)


def render_answer(model: Any) -> MaybeAnswer:
    """The answer's shape, for the answers section to lay out. `explanation` is
    not included — the section prints it once, the same way for every kind."""
    return load_all()[model.type].answer(model)
