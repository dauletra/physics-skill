"""The registry of slide types — the same shape as the question registry.

A slide type is one module declaring its spec, its place in the reading
order, and a reference fragment with worked examples. Registration happens on
import, so adding a slide kind is adding a module; the union of allowed
types, the JSON Schema, the reference and the conformance tests are all
derived from the registry.

What a slide type does **not** declare: a renderer. Slides are rendered by
the player, in the browser, from the emitted JSON — Python never writes
slide markup. That is the boundary that lets the player move to a server
later without the data noticing (docs/presentation.md §3).
"""

from __future__ import annotations

import importlib
import json
import pkgutil
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

from physics_svg.schema import Deferred
from physics_svg.visuals import visual_annotation

#: The worked examples live in the fragment, in fenced JSON blocks.
_JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)

if TYPE_CHECKING:  # mypy reads this as plain `Any`; at runtime it resolves
    VISUAL = Any
else:
    #: The illustration a slide may carry — the same union, the same
    #: validator and the same example library as a visual inside a document.
    VISUAL = Deferred(visual_annotation)


@dataclass(frozen=True)
class SlideType:
    #: Value of the `type` field in JSON.
    tag: str
    #: Human name for the generated reference.
    title: str
    model: type
    #: Place in everything a human reads — the reference index, the site —
    #: by where a slide sits in a lesson, not by its latin tag. Multiples of
    #: ten, so a new kind slots in without renumbering.
    order: int
    directory: Path

    @property
    def doc(self) -> Path:
        """Reference fragment for the model: fields, invariants, JSON."""
        return self.directory / f"{self.tag}.md"

    @property
    def card(self) -> Path:
        """Card for the teacher: what it is and what phrase produces it."""
        return self.directory / f"{self.tag}.card.md"

    @property
    def examples(self) -> list[dict[str, Any]]:
        """The worked slides from the fragment, in order of appearance.

        Each is a whole slide — the slide is the smallest thing that
        validates and the smallest thing the player shows. One source for
        every reader: the model reads them in the bundle, the suite parses
        them, the site will show them. An example that stops validating
        fails the build.
        """
        blocks = _JSON_BLOCK.findall(self.doc.read_text(encoding="utf-8"))
        if not blocks:
            raise ValueError(f"в {self.doc.name} нет примера в блоке ```json")
        return [json.loads(block) for block in blocks]

    @property
    def example(self) -> dict[str, Any]:
        """The canonical slide: the first example of the fragment."""
        return self.examples[0]


_REGISTRY: dict[str, SlideType] = {}
_LOADED = False


def register(*, tag: str, title: str, model: type, order: int, module: str) -> None:
    if tag in _REGISTRY:
        raise RuntimeError(f"slide type {tag!r} is already registered")
    taken = {entry.order: entry.tag for entry in _REGISTRY.values()}
    if order in taken:
        raise RuntimeError(f"order {order} is already taken by {taken[order]!r}")
    directory = Path(importlib.import_module(module).__file__ or "").parent
    _REGISTRY[tag] = SlideType(tag, title, model, order, directory)


def load_all() -> dict[str, SlideType]:
    """Every registered kind, in the order a person meets them in a lesson."""
    global _LOADED
    if not _LOADED:
        package = importlib.import_module("physics_svg.presentation.slides")
        for info in pkgutil.iter_modules(package.__path__):
            if info.name != "registry":
                importlib.import_module(f"physics_svg.presentation.slides.{info.name}")
        _LOADED = True
    return dict(sorted(_REGISTRY.items(), key=lambda item: item[1].order))


def slide_models() -> tuple[type, ...]:
    return tuple(entry.model for entry in load_all().values())


def slide_annotation() -> Any:
    """Union of every registered slide — assembled at runtime so no list has
    to be maintained by hand."""
    models = slide_models()
    if not models:
        raise RuntimeError("no slide types registered")
    return Union[models]
