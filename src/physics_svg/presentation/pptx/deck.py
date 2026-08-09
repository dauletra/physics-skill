"""A lesson as a deck: every slide asks its kind to lay itself out.

The counterpart of `presentation/emit.py:build_data`, and deliberately the
same shape — one pass over the validated models, each handing its own kind
the work. What differs is the destination: there the lesson became data for
the player to arrange, here it becomes the arrangement.

Every kind lays itself out — `register` will not take one that does not, so
there is no case here where a slide could be silently dropped.
"""

from __future__ import annotations

from typing import Any, Sequence

from physics_svg.presentation.manifest import PresentationSpec
from physics_svg.presentation.pptx.package import build_pptx
from physics_svg.presentation.slides.registry import load_all


def build_deck(
    presentation: PresentationSpec, slides: Sequence[Any]
) -> tuple[bytes, tuple[str, ...]]:
    """The finished .pptx of one lesson, and what it could not say.

    The notes are formulas outside the OMML subset, named by the slide they
    stand on. Same shape as `build_docx`: the deck is finished and correct,
    and these are the lines a teacher has to know about before the lesson
    rather than during it.
    """
    registry = load_all()
    built = []
    notes: list[str] = []
    for number, model in enumerate(slides, start=1):
        slide = registry[model.type].build(model)
        built.append(slide)
        notes.extend(f"слайд {number}: {note}" for note in slide.notes)
    return build_pptx(built, title=presentation.title), tuple(notes)
