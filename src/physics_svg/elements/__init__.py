"""Physical drawing vocabulary built on `draw`.

Structures that recur across illustrations live here so that a new visual
type is an arrangement of known elements rather than a fresh tick loop. The
layer grows only when a type actually needs a new element — arrows, angle
marks and dimension lines arrive with the mechanics types that require them,
not in advance.
"""

from physics_svg.elements.arrow import (
    HEAD_LENGTH,
    LABEL_BIAS,
    LABEL_GAP,
    LABEL_SIZE,
    angle_mark,
    arrow,
    label_near,
    signed_angle_span,
    vector_sum,
)
from physics_svg.elements.fills import HATCH_SPACING, LIQUID_SPACING, hatch, liquid
from physics_svg.elements.scale import (
    FINE_DIVISIONS,
    ArcAxis,
    Axis,
    LinearAxis,
    Tick,
    division_count,
    label_every,
    nice_ticks,
    scale_marks,
    subdivisions,
    tick_layout,
)

__all__ = [
    "ArcAxis",
    "Axis",
    "FINE_DIVISIONS",
    "HATCH_SPACING",
    "HEAD_LENGTH",
    "LABEL_BIAS",
    "LABEL_GAP",
    "LABEL_SIZE",
    "LIQUID_SPACING",
    "LinearAxis",
    "Tick",
    "angle_mark",
    "arrow",
    "division_count",
    "hatch",
    "label_every",
    "label_near",
    "liquid",
    "nice_ticks",
    "scale_marks",
    "signed_angle_span",
    "subdivisions",
    "tick_layout",
    "vector_sum",
]
