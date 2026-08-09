"""An illustration on a slide.

The shapes themselves come from the drawing layer, from the same nodes the
SVG is built from; what this module knows is the part that is about a
*slide* — which box the picture has, and where inside that box it ends up.

**Native shapes, not an image.** A graph in the deck is lines, curves and
labels a teacher can select, move and print at any size — the same decision
the Word backend took, and for the same reason. An embedded SVG would need
a raster fallback for older PowerPoint and would take the picture out of the
teacher's hands (docs/pptx.md §5.4).

**Centred in its box.** The picture keeps its proportions, so it fills the
box in one direction and has room to spare in the other; that room goes to
both sides. A picture pinned to the top left of its box would leave the
slide looking as if something had failed to load.
"""

from __future__ import annotations

from typing import Any

from physics_svg.presentation.pptx import design
from physics_svg.visuals import build_slide_shapes


def picture(model: Any, box: tuple[float, float, float, float]) -> str:
    """One illustration, laid into `box` — (x, y, width, height) in points."""
    x, y, width, height = box
    group, cx, cy = build_slide_shapes(
        model, width_emu=design.emu(width), height_emu=design.emu(height)
    )
    left = design.emu(x) + (design.emu(width) - cx) // 2
    top = design.emu(y) + (design.emu(height) - cy) // 2
    return _placed(group, left, top, cx, cy)


def _placed(group: str, x: int, y: int, cx: int, cy: int) -> str:
    """The group moved to where it belongs.

    The offset goes on the group's own `a:xfrm` rather than on every child:
    `a:chOff`/`a:chExt` already declare that the children speak in the
    picture's own coordinates, so moving the group moves the drawing and
    leaves the arithmetic inside it untouched.
    """
    old = (
        f'<a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="{cx}" cy="{cy}"/>'
    )
    new = (
        f'<a:off x="{x}" y="{y}"/><a:ext cx="{cx}" cy="{cy}"/>'
        f'<a:chOff x="0" y="0"/><a:chExt cx="{cx}" cy="{cy}"/>'
    )
    if old not in group:  # pragma: no cover - the drawing layer's own shape
        raise ValueError("группа фигур не той формы, чтобы её можно было сдвинуть")
    return group.replace(old, new, 1)
