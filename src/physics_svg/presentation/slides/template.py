"""A template — a named, filled-in slide of an existing kind.

The difference from a slide kind is the difference between a contract and a
starting point (docs/slide-templates.md §2): a kind brings fields, a
validator, an emitter and a layout of its own; a template brings one JSON
file and a line saying when to take it. The model copies the file and edits
it, exactly as it copies an illustration spec out of `library/`.

The envelope exists because the slide schema is strict — an extra key beside
a slide is an error — and the name and the "when" have to live somewhere:

    {"template": "with-answer", "when": "…", "slide": {"type": "board_task", …}}

`slide` is a whole slide, not a fragment: a slide is the smallest thing that
validates and the smallest thing the player shows. By build time the
envelope is gone — the bundle ships the slide alone, and nothing downstream
of validation knows templates exist.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from physics_svg.schema import Deferred, field, parse, spec


def _slide_annotation() -> Any:
    # Resolved on first use, not on import: the registry owns the union and
    # is the module that reads templates, so the dependency has to point
    # this way round.
    from physics_svg.presentation.slides.registry import slide_annotation

    return slide_annotation()


if TYPE_CHECKING:  # mypy reads this as plain `Any`; at runtime it resolves
    SLIDE = Any
else:
    SLIDE = Deferred(_slide_annotation)


@spec
class TemplateSpec:
    """Заготовка слайда: имя, повод взять и сам слайд."""

    template: str = field(doc="Слаг шаблона; совпадает с именем файла")
    when: str = field(doc="Одна строка: когда брать этот шаблон")
    slide: SLIDE = field(doc="Целый слайд — то, что копируют и заполняют")


@dataclass(frozen=True)
class SlideTemplate:
    """One template file, read and validated."""

    #: File name without extension — how the catalogue and the reference
    #: fragment address it.
    slug: str
    #: One line: when to take this one.
    when: str
    #: The slide as JSON — what gets copied. Kept raw rather than as a model
    #: for the same reason the draft is kept raw: what the author wrote must
    #: survive verbatim, not as a normalised round-trip.
    slide: dict[str, Any]
    path: Path


def load_template(path: Path) -> SlideTemplate:
    """Read one template file, validating the envelope and the slide inside."""
    raw = json.loads(path.read_text(encoding="utf-8"))
    model = parse(TemplateSpec, raw, name=path.name)
    if model.template != path.stem:
        raise ValueError(
            f"{path.name}: 'template' — '{model.template}', а файл называется "
            f"'{path.stem}'; имя шаблона и имя файла должны совпадать"
        )
    return SlideTemplate(model.template, model.when, raw["slide"], path)
