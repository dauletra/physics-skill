"""Texture fills: hatching for solids, level lines for liquids.

Both are drawn as explicit lines clipped to the region rather than as a
pattern. A pattern would need a clip path to stop at the shape edge, and for
the small areas these fills cover (a block between caliper jaws, water in a
measuring cylinder) the explicit form is fewer nodes and exactly bounded —
which also means the canvas can measure it.

The conventions are the ones school textbooks use: 45-degree hatching means
"solid body", evenly spaced horizontal lines mean "liquid".
"""

from __future__ import annotations

import math

from physics_svg.draw import HAIR, BBox, Line, Node, Pt, Style

#: Distance between hatch lines, measured perpendicular to them.
HATCH_SPACING = 4.5
#: Distance between liquid level lines.
LIQUID_SPACING = 4.0


def hatch(region: BBox, spacing: float = HATCH_SPACING, style: Style = HAIR) -> list[Node]:
    """45-degree hatching filling `region` — the "this is a solid" mark."""
    nodes: list[Node] = []
    height = region.height
    stride = spacing * math.sqrt(2)
    offset = stride
    while offset < region.width + height:
        ax, ay = region.x0 + offset, region.y0
        if ax > region.x1:
            ay = region.y0 + (ax - region.x1)
            ax = region.x1
        bx, by = region.x0 + offset - height, region.y1
        if bx < region.x0:
            by = region.y1 - (region.x0 - bx)
            bx = region.x0
        nodes.append(Line(Pt(ax, ay), Pt(bx, by), style))
        offset += stride
    return nodes


def liquid(
    region: BBox, spacing: float = LIQUID_SPACING, style: Style = HAIR, inset: float = 1.5
) -> list[Node]:
    """Horizontal level lines filling `region` downward from its top.

    `inset` keeps the lines off the vessel walls so the contour stays a
    contour.
    """
    nodes: list[Node] = []
    y = region.y0 + spacing
    while y < region.y1:
        nodes.append(Line(Pt(region.x0 + inset, y), Pt(region.x1 - inset, y), style))
        y += spacing
    return nodes
