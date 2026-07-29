"""The registry of question types — the same shape as the visual registry.

A question type is one module declaring four things: its spec, the **body**
(what the student sees — blank fields, unmarked options), the **answer** (a
compact line for the answers section) and a reference fragment. Registration
happens on import, so adding a pedagogical kind is adding a module.

Why two renderers and not a mode flag: a task body never contains answers at
all. The handout variant is the same document without the answers section,
not a second rendering of the same bodies — which is what makes it
impossible to leak an answer into a printed sheet by forgetting a flag.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

Renderer = Callable[[Any], str]


@dataclass(frozen=True)
class QuestionType:
    #: Value of the `type` field in JSON.
    tag: str
    #: Human name for the generated reference.
    title: str
    model: type
    #: What is printed in place of the task.
    body: Renderer
    #: The compact form for the answers section; empty means "no answer"
    #: (an `open` question asked without one).
    answer: Renderer
    directory: Path

    @property
    def doc(self) -> Path:
        return self.directory / f"{self.tag}.md"


_REGISTRY: dict[str, QuestionType] = {}
_LOADED = False


def register(
    *, tag: str, title: str, model: type, body: Renderer, answer: Renderer, module: str
) -> None:
    if tag in _REGISTRY:
        raise RuntimeError(f"question type {tag!r} is already registered")
    directory = Path(importlib.import_module(module).__file__ or "").parent
    _REGISTRY[tag] = QuestionType(tag, title, model, body, answer, directory)


def load_all() -> dict[str, QuestionType]:
    global _LOADED
    if not _LOADED:
        package = importlib.import_module("physics_svg.document.questions")
        for info in pkgutil.iter_modules(package.__path__):
            if info.name != "registry":
                importlib.import_module(f"physics_svg.document.questions.{info.name}")
        _LOADED = True
    return dict(sorted(_REGISTRY.items()))


def question_models() -> tuple[type, ...]:
    return tuple(entry.model for entry in load_all().values())


def is_question(model: object) -> bool:
    return isinstance(model, question_models())


def render_body(model: Any) -> str:
    return load_all()[model.type].body(model)


def render_answer(model: Any) -> str:
    """The compact answer, ready for the answers section. `explanation` is not
    included — the section prints it once, the same way for every kind."""
    return load_all()[model.type].answer(model)
