"""A lesson as a deck: every slide asks its kind to lay itself out.

The counterpart of `presentation/emit.py:build_data`, and deliberately the
same shape — one pass over the validated models, each handing its own kind
the work. What differs is the destination: there the lesson became data for
the player to arrange, here it becomes the arrangement.

A kind that has no layout yet is named, loudly, with the phase that will
give it one. Silence would produce a lesson with slides missing from the
middle and nothing to say why.
"""

from __future__ import annotations

from typing import Any, Sequence

from physics_svg.presentation.manifest import PresentationSpec
from physics_svg.presentation.pptx.package import build_pptx
from physics_svg.presentation.slides.registry import PLAYER_ONLY, load_all


def build_deck(presentation: PresentationSpec, slides: Sequence[Any]) -> bytes:
    """The finished .pptx of one lesson."""
    registry = load_all()
    built = []
    for number, model in enumerate(slides, start=1):
        kind = registry[model.type]
        if kind.build is None:
            phase = "P4" if model.type in PLAYER_ONLY else "?"
            raise NotImplementedError(
                f"слайд {number}: вид '{model.type}' ещё не раскладывается "
                f"в PowerPoint — это фаза {phase} плана docs/pptx.md"
            )
        built.append(kind.build(model))
    return build_pptx(built, title=presentation.title)
