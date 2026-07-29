"""Arrows and angle marks — the vocabulary of a vector drawing.

Deliberately absent until now: the library grows an element when a type
actually needs it, not in advance. These arrive with the vector diagrams.

An arrow is a line with a filled head, and the line stops *short* of the tip
so the stroke does not thicken the point. An angle mark is an arc between two
directions with its label on the bisector — where a textbook puts it.
"""

from __future__ import annotations

import math

from physics_svg.draw import (
    BLACK,
    HEAVY,
    Line,
    Node,
    Polyline,
    Pt,
    Style,
    Text,
    arc,
    direction,
    polar,
)

#: Head proportions in user units. Fixed rather than proportional to length:
#: a short vector with a tiny head reads as a line segment, and a long one
#: with a huge head reads as a signpost.
HEAD_LENGTH = 7.0
HEAD_HALF_WIDTH = 3.0

#: Where a label sits relative to the point it names.
LABEL_GAP = 4.0
LABEL_SIZE = 9.0

#: How far an angle label leans from the bisector towards the first arm.
LABEL_BIAS = 0.2

_HEAD = Style(fill=BLACK)


def arrow(start: Pt, end: Pt, style: Style = HEAVY, head_length: float = HEAD_LENGTH) -> list[Node]:
    """A vector from `start` to `end`."""
    span = end - start
    length = span.length()
    if length == 0:
        return []
    unit = span.normalized()
    head_length = min(head_length, length)
    base = end - unit * head_length
    across = unit.perpendicular() * HEAD_HALF_WIDTH
    return [
        Line(start, base, style),
        Polyline((end, base + across, base - across), _HEAD, closed=True),
    ]


def label_near(at: Pt, away: Pt, text: str, size: float = LABEL_SIZE) -> Text:
    """Place a label beside a point, pushed along `away`.

    The anchor follows the direction, so a label to the left of the drawing
    grows leftwards instead of overhanging the picture.
    """
    unit = away.normalized()
    position = at + unit * LABEL_GAP
    if unit.x > 0.35:
        anchor, dx = "start", 1.0
    elif unit.x < -0.35:
        anchor, dx = "end", -1.0
    else:
        anchor, dx = "middle", 0.0
    # Vertical nudge: a label above the point sits on its own baseline, one
    # below has to clear the ascender.
    dy = -1.0 if unit.y < -0.35 else (size * 0.7 if unit.y > 0.35 else size * 0.3)
    return Text(position.shifted(dx, dy), text, size, anchor)


def angle_mark(
    center: Pt,
    from_deg: float,
    to_deg: float,
    radius: float,
    label: str | None = None,
    style: Style = Style(stroke=BLACK, width=0.8, fill="none"),
    size: float = 8.0,
) -> list[Node]:
    """An arc between two directions, with its label on the bisector."""
    nodes: list[Node] = [arc(center, radius, from_deg, to_deg, style)]
    if label:
        # Leaning towards the first arm rather than sitting exactly on the
        # bisector: on a common vertex that is where a resultant runs.
        middle = from_deg + (to_deg - from_deg) * (0.5 - LABEL_BIAS)
        at = polar(center, radius + LABEL_GAP + size * 0.4, middle)
        nodes.append(label_near(at, direction(middle), label, size))
    return nodes


def signed_angle_span(from_deg: float, to_deg: float) -> float:
    """The shorter way round from one direction to the other, in degrees."""
    return (to_deg - from_deg + 180.0) % 360.0 - 180.0


def vector_sum(vectors: list[tuple[float, float]]) -> tuple[float, float]:
    """Resultant of (length, angle) pairs, as a (length, angle) pair."""
    x = sum(length * math.cos(math.radians(angle)) for length, angle in vectors)
    y = sum(length * math.sin(math.radians(angle)) for length, angle in vectors)
    return math.hypot(x, y), math.degrees(math.atan2(y, x))
