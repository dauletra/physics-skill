"""The illustration library: one package per type.

    visuals/<type>/
        model.py      spec and its invariants
        render.py     draws with elements, not with SVG strings
        specs/*.json  examples — gallery, goldens, and the library the
                      skill ships so the model edits rather than invents
        doc.md        reference fragment for the model (dense)
        card.md       gallery card for the teacher (what it is, when to use)

See registry.py for what a type declares.
"""

from physics_svg.visuals.registry import (
    Layout,
    VisualType,
    build_shapes,
    build_slide_shapes,
    build_svg,
    label_metrics,
    load_all,
    parse_visual,
    register,
    render_to_canvas,
    visual_annotation,
    visual_type,
)

__all__ = [
    "Layout",
    "VisualType",
    "build_shapes",
    "build_slide_shapes",
    "build_svg",
    "label_metrics",
    "load_all",
    "parse_visual",
    "register",
    "render_to_canvas",
    "visual_annotation",
    "visual_type",
]
