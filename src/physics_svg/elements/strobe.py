"""A stroboscopic trail: where a body was at equal intervals of time.

The element a flash photograph makes. Marks at equal *times* — not at equal
distances — are what turns a line into a statement about motion: evenly
spaced means uniform, crowding means slowing down. That is also why the
trail cannot be replaced by a named curve; the curve is what the marks come
out as, not what they are.

Arrives with `frames`, where the same motion is stamped twice and the two
rows of marks are the comparison the picture exists for.
"""

from __future__ import annotations

from typing import Sequence

from physics_svg.draw import LINE, SOLID, Circle, Node, Polyline, Pt, Style

#: Radius of one mark, in user units. Fixed rather than a fraction of the
#: trail: marks are read as positions of one body, and a body does not grow
#: because its journey was longer.
MARK_RADIUS = 2.2


def strobe(
    points: Sequence[Pt],
    *,
    radius: float = MARK_RADIUS,
    style: Style = LINE,
) -> list[Node]:
    """The path through `points`, with a mark at each of them.

    A body that stays put — every mark on the same spot — draws one mark and
    no path: a polyline of coincident points is a stroke of zero length that
    some renderers still cap into a blob.
    """
    if not points:
        return []
    distinct = _distinct(points)
    nodes: list[Node] = []
    if len(distinct) > 1:
        nodes.append(Polyline(tuple(points), style))
    for point in distinct:
        nodes.append(Circle(point, radius, SOLID))
    return nodes


def _distinct(points: Sequence[Pt]) -> list[Pt]:
    seen: list[Pt] = []
    for point in points:
        if not any(abs(point.x - kept.x) < 1e-9 and abs(point.y - kept.y) < 1e-9 for kept in seen):
            seen.append(point)
    return seen
