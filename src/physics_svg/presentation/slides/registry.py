"""The registry of slide types — the same shape as the question registry.

A slide type is one package declaring its spec, its place in the reading
order, its documentation and its templates. Registration happens on import,
so adding a slide kind is adding a directory; the union of allowed types,
the JSON Schema, the reference, the template catalogue and the conformance
tests are all derived from the registry.

What a slide type does **not** declare: a renderer. Slides are rendered by
the player, in the browser, from the emitted JSON — Python never writes
slide markup. What a type does declare is **emit**: which of its fields are
author text to be parsed into runs, and which are visuals — serialisation
to the wire, markup-free by construction because the vocabulary it writes
into is JSON. That is the boundary that lets the player move to a server
later without the data noticing (docs/presentation.md §3).
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Union

from physics_svg.presentation.slides.template import SlideTemplate, load_template
from physics_svg.schema import Deferred
from physics_svg.visuals import visual_annotation

#: The slide's payload as wire data: parsed runs for author text, an emitted
#: visual for an illustration. The second argument is the id scope for the
#: slide's SVG — unique per slide, so two graphs on one page cannot collide.
Emitter = Callable[[Any, str], dict[str, Any]]

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
    #: Serialisation to the wire — data, never markup.
    emit: Emitter
    #: Place in everything a human reads — the reference index, the site —
    #: by where a slide sits in a lesson, not by its latin tag. Multiples of
    #: ten, so a new kind slots in without renumbering.
    order: int
    #: The type's package directory: templates/, doc.md, card.md live here.
    directory: Path

    @property
    def doc(self) -> Path:
        """Reference fragment for the model: fields, invariants, JSON."""
        return self.directory / "doc.md"

    @property
    def card(self) -> Path:
        """Card for the teacher: what it is and what phrase produces it."""
        return self.directory / "card.md"

    @property
    def templates(self) -> list[SlideTemplate]:
        """The kind's starting points, in file-name order.

        One source for every reader: the model copies them out of the
        bundle's `library/slides/`, the reference shows them, the suite
        parses and emits them. A template that stops validating fails the
        build (docs/slide-templates.md §7).
        """
        paths = sorted((self.directory / "templates").glob("*.json"))
        if not paths:
            raise ValueError(
                f"у вида '{self.tag}' нет ни одного шаблона: заведи "
                f"{self.tag}/templates/<слаг>.json"
            )
        return [load_template(path) for path in paths]

    @property
    def examples(self) -> list[dict[str, Any]]:
        """Every template's slide — whole slides, not fragments."""
        return [template.slide for template in self.templates]

    @property
    def example(self) -> dict[str, Any]:
        """The canonical slide: the kind's first template."""
        return self.examples[0]


_REGISTRY: dict[str, SlideType] = {}
_LOADED = False


def register(
    *, tag: str, title: str, model: type, emit: Emitter, order: int, module: str
) -> None:
    if tag in _REGISTRY:
        raise RuntimeError(f"slide type {tag!r} is already registered")
    taken = {entry.order: entry.tag for entry in _REGISTRY.values()}
    if order in taken:
        raise RuntimeError(f"order {order} is already taken by {taken[order]!r}")
    directory = Path(importlib.import_module(module).__file__ or "").parent
    _REGISTRY[tag] = SlideType(tag, title, model, emit, order, directory)


def load_all() -> dict[str, SlideType]:
    """Every registered kind, in the order a person meets them in a lesson."""
    global _LOADED
    if not _LOADED:
        package = importlib.import_module("physics_svg.presentation.slides")
        for info in pkgutil.iter_modules(package.__path__):
            if info.ispkg:  # a kind is a package; registry.py and template.py are not
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
