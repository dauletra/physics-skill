"""Graduated scales — the single most reused structure in physics drawings.

A ruler, a measuring cylinder, a dial ammeter, a stopwatch face and a vernier
caliper differ in where the marks sit, not in how they are computed. This
module separates those two questions:

* an **axis** answers "where is fraction 0..1 of the scale, and which way do
  its ticks grow" — straight (`LinearAxis`) or curved (`ArcAxis`);
* `tick_layout()` answers "which values get a mark, and which of them get a
  number" — the arithmetic of divisions and label thinning.

`scale_marks()` then draws the two together, so a new instrument family costs
an axis definition rather than a tick loop.

Label thinning is **presentation**, and lives here rather than in a model:
when the label step is part of the problem ("determine the scale division"),
the author pins it explicitly and this module obeys.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Callable, Sequence

from physics_svg.draw import LINE, THIN, Line, Node, Pt, Style, Text, direction, num, polar

#: Label steps that read as "round" on a real instrument: the normalised
#: mantissa is 1, 2 or 5. A ruler with 2.5 mm ticks is numbered every 5 mm,
#: never every 2.5.
_ROUND_MANTISSAS = frozenset({(1,), (2,), (5,)})

#: How many parts a fine grid splits one labelled division into. Ten — like
#: real graph paper — would put lines about three pixels apart at the target
#: width and read as noise instead of a grid.
FINE_DIVISIONS = 5


@dataclass(frozen=True)
class Tick:
    value: float
    fraction: float
    labeled: bool


# --- axes ---------------------------------------------------------------


class Axis:
    """Maps a scale fraction to a point and a tick direction."""

    def point(self, fraction: float) -> Pt:
        raise NotImplementedError

    def outward(self, fraction: float) -> Pt:
        """Unit vector along which ticks grow away from the scale line."""
        raise NotImplementedError


@dataclass(frozen=True)
class LinearAxis(Axis):
    """Straight scale: a ruler edge, a cylinder wall, a vernier bar."""

    start: Pt
    end: Pt
    #: Direction ticks grow in; normalised on use.
    tick_direction: Pt

    def point(self, fraction: float) -> Pt:
        return self.start.lerp(self.end, fraction)

    def outward(self, fraction: float) -> Pt:
        return self.tick_direction.normalized()


@dataclass(frozen=True)
class ArcAxis(Axis):
    """Curved scale: a dial arc or a full stopwatch face.

    Angles are textbook degrees. A dial runs from 150 deg to 30 deg so the
    needle sweeps through the vertical; a clock face runs from 90 deg to
    -270 deg, i.e. from the top, clockwise, all the way round.
    """

    center: Pt
    radius: float
    start_deg: float
    end_deg: float

    def angle(self, fraction: float) -> float:
        return self.start_deg + (self.end_deg - self.start_deg) * fraction

    def point(self, fraction: float) -> Pt:
        return polar(self.center, self.radius, self.angle(fraction))

    def outward(self, fraction: float) -> Pt:
        return direction(self.angle(fraction))


# --- tick arithmetic ----------------------------------------------------


def division_count(minimum: float, maximum: float, step: float) -> int:
    return round((maximum - minimum) / step)


def label_every(step: float, divisions: int, max_labels: int) -> int:
    """Number every k-th tick.

    Candidates are ranked: a "round" label step in units of the quantity
    wins first (and must produce at least two labelled intervals), then one
    that divides the scale evenly, then the densest that fits the limit.
    """
    fitting = [k for k in range(1, divisions + 1) if divisions // k + 1 <= max_labels]
    if not fitting:
        fitting = [divisions]

    def rank(k: int) -> tuple[bool, bool, int]:
        mantissa = (Decimal(str(step)) * k).normalize().as_tuple().digits
        pretty = mantissa in _ROUND_MANTISSAS and divisions // k >= 2
        return (not pretty, divisions % k != 0, k)

    return min(fitting, key=rank)


def division_values(minimum: float, maximum: float, step: float) -> list[float]:
    """Every division of `step` counted from `minimum`, the far end included.

    Counted from the start of the scale rather than from round multiples of
    the step: an author who pins the step means "cells of this size, from
    where my axis begins".
    """
    return [minimum + i * step for i in range(division_count(minimum, maximum, step) + 1)]


def ticks_at(
    values: Sequence[float], low: float, high: float, *, label_every: int = 1
) -> tuple[Tick, ...]:
    """Place scale values on the interval [low, high], numbering every k-th.

    Unlike `tick_layout`, the fraction is measured against the interval and
    not against the ticks themselves: a graph axis carries divisions that
    need not reach its ends, and each must still land where its value is.
    """
    span = high - low
    return tuple(
        Tick(value, (value - low) / span, i % label_every == 0)
        for i, value in enumerate(values)
    )


def tick_layout(
    minimum: float,
    maximum: float,
    step: float,
    *,
    max_labels: int,
    label_step: float | None = None,
) -> tuple[Tick, ...]:
    """Every tick of a scale, with the ones that carry a number marked.

    The end of the scale is always numbered — its measuring limit is read in
    every problem about ranges — and a regular label closer than half a step
    to it is dropped so the two numbers do not collide.
    """
    divisions = division_count(minimum, maximum, step)
    if label_step is not None:
        every = round(label_step / step)
    else:
        every = label_every(step, divisions, max_labels)
    ticks = []
    for i in range(divisions + 1):
        labeled = i == divisions or (i % every == 0 and (divisions - i) * 2 >= every)
        ticks.append(Tick(minimum + i * step, i / divisions, labeled))
    return tuple(ticks)


def nice_ticks(low: float, high: float, max_ticks: int = 9) -> list[float]:
    """Round gridline positions for a continuous range.

    Step is 1, 2 or 5 times a power of ten — the densest that fits
    `max_ticks` inside the range. A student reads values off this grid, so a
    step of "range / 5" landing on 3.7 would be a defect, not a nicety.
    """
    span = high - low
    base_exponent = math.floor(math.log10(span)) - 2
    for exponent in range(base_exponent, base_exponent + 5):
        for mantissa in (1, 2, 5):
            step = mantissa * 10**exponent
            first = math.ceil(low / step - 1e-9)
            last = math.floor(high / step + 1e-9)
            if 2 <= last - first + 1 <= max_ticks:
                return [n * step for n in range(first, last + 1)]
    return [low, high]


def subdivisions(ticks: Sequence[float], low: float, high: float) -> list[float]:
    """Fine gridlines between labelled ones, across the whole range.

    The outermost labelled ticks usually sit inside the range (250..650 is
    numbered from 300), so the fine grid is extended past them rather than
    stopping short.
    """
    if len(ticks) < 2:
        return []
    step = (ticks[1] - ticks[0]) / FINE_DIVISIONS
    first = math.ceil((low - ticks[0]) / step - 1e-9)
    last = math.floor((high - ticks[0]) / step + 1e-9)
    return [
        ticks[0] + n * step
        for n in range(first, last + 1)
        # Labelled divisions are drawn separately, heavier and darker.
        if n % FINE_DIVISIONS != 0
    ]


# --- drawing ------------------------------------------------------------


def scale_marks(
    axis: Axis,
    ticks: Sequence[Tick],
    *,
    major_length: float,
    minor_length: float,
    mid_length: float | None = None,
    label_distance: float | None = None,
    label_direction: Pt | None = None,
    label_anchor: str = "middle",
    label_size: float = 7.0,
    label_shift: float = 0.0,
    formatter: Callable[[float], str] = num,
    major_style: Style = LINE,
    minor_style: Style = THIN,
    skip: Sequence[int] = (),
) -> list[Node]:
    """Draw ticks and their numbers along `axis`.

    `mid_length` gives the half-way tick its own length, the way a ruler
    marks 5 mm between numbered centimetres; it is used only when the label
    step is even. `label_distance` of `None` draws ticks without numbers.
    `skip` drops ticks by index — a full clock face needs it, because its
    first and last tick are the same point.
    """
    labeled_indices = [i for i, tick in enumerate(ticks) if tick.labeled]
    every = labeled_indices[1] - labeled_indices[0] if len(labeled_indices) > 1 else 1
    nodes: list[Node] = []
    for i, tick in enumerate(ticks):
        if i in skip:
            continue
        base = axis.point(tick.fraction)
        outward = axis.outward(tick.fraction)
        if tick.labeled:
            length, style = major_length, major_style
        elif mid_length is not None and every >= 4 and every % 2 == 0 and i % (every // 2) == 0:
            length, style = mid_length, minor_style
        else:
            length, style = minor_length, minor_style
        nodes.append(Line(base, base + outward * length, style))
        if tick.labeled and label_distance is not None:
            towards = (label_direction or outward).normalized()
            at = base + towards * label_distance
            nodes.append(
                Text(
                    at.shifted(0, label_shift),
                    formatter(tick.value),
                    size=label_size,
                    anchor=label_anchor,
                )
            )
    return nodes
