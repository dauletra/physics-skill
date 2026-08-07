"""Slide types: one module per kind of slide.

    slides/<tag>.py         spec + register()
    slides/<tag>.md         reference fragment for the model, worked examples
    slides/<tag>.card.md    card for the teacher, shown on the site

See registry.py for the contract. Unlike a question type, a slide registers
no renderer: slides are rendered by the player from the emitted JSON, and
Python never writes slide markup.
"""

from physics_svg.presentation.slides.registry import (
    SlideType,
    load_all,
    register,
    slide_annotation,
    slide_models,
)

__all__ = [
    "SlideType",
    "load_all",
    "register",
    "slide_annotation",
    "slide_models",
]
