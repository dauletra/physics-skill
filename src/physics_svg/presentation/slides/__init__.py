"""Slide types: one package per kind of slide.

    slides/<tag>/__init__.py        spec + build + register()
    slides/<tag>/doc.md             reference fragment for the model
    slides/<tag>/card.md            card for the teacher, shown on the site
    slides/<tag>/templates/*.json   the kind's starting points

See registry.py for the contract. A template is not a kind — it is a filled
in slide of an existing one; see template.py and docs/slide-templates.md.
"""

from physics_svg.presentation.slides.registry import (
    SlideType,
    load_all,
    register,
    slide_annotation,
    slide_models,
)
from physics_svg.presentation.slides.template import SlideTemplate, load_template

__all__ = [
    "SlideTemplate",
    "SlideType",
    "load_all",
    "load_template",
    "register",
    "slide_annotation",
    "slide_models",
]
