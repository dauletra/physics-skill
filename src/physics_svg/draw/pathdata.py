"""Path data as structure rather than as a string.

`Path` stores its `d` the way SVG wants it, which is fine while SVG is the
only output. A second backend has to know where the path actually goes — and
so does any transform applied to it — so this module turns `d` back into
segments and back into a string.

Only what the library emits is understood: absolute `M`, `L`, `A`, `C`, `Z`,
numbers separated by commas or spaces, and the SVG rule that extra numbers
repeat the previous command. Arcs are always circular here (`PathBuilder`
and `arc()` never produce elliptical ones), which is what lets the geometry
below stay short.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterator, Sequence, Union

from physics_svg.draw.geometry import Pt
from physics_svg.draw.text import num

#: Arcs are sampled at this step when a transform makes a true arc
#: impossible. Five degrees is well below what print resolves.
SAMPLE_DEG = 5.0

_TOKEN = re.compile(r"([MLACZmlacz])|(-?\d*\.?\d+(?:[eE][-+]?\d+)?)")


@dataclass(frozen=True)
class Move:
    to: Pt


@dataclass(frozen=True)
class LineTo:
    to: Pt


@dataclass(frozen=True)
class CurveTo:
    c1: Pt
    c2: Pt
    to: Pt


@dataclass(frozen=True)
class ArcTo:
    """Circular arc, in SVG's endpoint parametrisation."""

    radius: float
    large: int
    sweep: int
    to: Pt


@dataclass(frozen=True)
class Close:
    pass


Segment = Union[Move, LineTo, CurveTo, ArcTo, Close]


class PathSyntax(ValueError):
    """`d` uses something this project does not emit."""


def parse(d: str) -> tuple[Segment, ...]:
    """Segments of a path, in order."""
    letters: list[str] = []
    numbers: list[list[float]] = []
    for match in _TOKEN.finditer(d):
        letter, number = match.group(1), match.group(2)
        if letter is not None:
            if letter.islower():
                raise PathSyntax(f"относительная команда '{letter}' не поддерживается")
            letters.append(letter)
            numbers.append([])
        elif not letters:
            raise PathSyntax(f"путь начинается не с команды: {d!r}")
        else:
            numbers[-1].append(float(number))

    segments: list[Segment] = []
    for letter, args in zip(letters, numbers):
        segments.extend(_expand(letter, args))
    return tuple(segments)


def _expand(letter: str, args: list[float]) -> Iterator[Segment]:
    """One command letter and its numbers. Extra numbers repeat the command;
    after `M` they repeat as `L`, which is what SVG says and what the ruling
    tiles rely on (`M12 0 L0 0 0 12`)."""
    if letter == "Z":
        yield Close()
        return
    sizes = {"M": 2, "L": 2, "C": 6, "A": 7}
    step = sizes[letter]
    if not args or len(args) % step:
        raise PathSyntax(f"команда '{letter}': ожидалось кратное {step} чисел, получено {len(args)}")
    for i in range(0, len(args), step):
        chunk = args[i : i + step]
        if letter == "M":
            yield Move(Pt(chunk[0], chunk[1])) if i == 0 else LineTo(Pt(chunk[0], chunk[1]))
        elif letter == "L":
            yield LineTo(Pt(chunk[0], chunk[1]))
        elif letter == "C":
            yield CurveTo(Pt(chunk[0], chunk[1]), Pt(chunk[2], chunk[3]), Pt(chunk[4], chunk[5]))
        else:
            if chunk[0] != chunk[1] or chunk[2] != 0:
                raise PathSyntax("поддерживаются только круговые дуги без поворота осей")
            yield ArcTo(chunk[0], int(chunk[3]), int(chunk[4]), Pt(chunk[5], chunk[6]))


def to_d(segments: Sequence[Segment]) -> str:
    """Segments back to `d`, formatted the way the nodes format numbers."""
    parts: list[str] = []
    for segment in segments:
        if isinstance(segment, Move):
            parts.append(f"M{num(segment.to.x)},{num(segment.to.y)}")
        elif isinstance(segment, LineTo):
            parts.append(f"L{num(segment.to.x)},{num(segment.to.y)}")
        elif isinstance(segment, CurveTo):
            parts.append(
                f"C{num(segment.c1.x)},{num(segment.c1.y)} "
                f"{num(segment.c2.x)},{num(segment.c2.y)} "
                f"{num(segment.to.x)},{num(segment.to.y)}"
            )
        elif isinstance(segment, ArcTo):
            parts.append(
                f"A{num(segment.radius)},{num(segment.radius)} 0 "
                f"{segment.large} {segment.sweep} {num(segment.to.x)},{num(segment.to.y)}"
            )
        else:
            parts.append("Z")
    return " ".join(parts)


# --- arc geometry -------------------------------------------------------


@dataclass(frozen=True)
class ArcGeometry:
    """The same arc as a centre, a starting angle and a sweep — the form both
    a sampler and DrawingML need. Angles are in screen degrees: measured from
    the positive x axis, growing clockwise, because y points down."""

    center: Pt
    radius: float
    start_deg: float
    sweep_deg: float


def arc_geometry(start: Pt, segment: ArcTo) -> ArcGeometry:
    """Endpoint parametrisation -> centre parametrisation (SVG F.6.5)."""
    radius = segment.radius
    end = segment.to
    dx, dy = (start.x - end.x) / 2, (start.y - end.y) / 2
    squared = dx * dx + dy * dy
    if squared == 0 or radius == 0:
        return ArcGeometry(start, 0.0, 0.0, 0.0)
    # A radius too small for the chord is stretched to fit, as SVG requires.
    radius = max(radius, math.sqrt(squared))
    factor = math.sqrt(max(0.0, radius * radius / squared - 1.0))
    if segment.large == segment.sweep:
        factor = -factor
    cx = factor * dy + (start.x + end.x) / 2
    cy = -factor * dx + (start.y + end.y) / 2
    center = Pt(cx, cy)
    start_deg = math.degrees(math.atan2(start.y - cy, start.x - cx))
    end_deg = math.degrees(math.atan2(end.y - cy, end.x - cx))
    sweep = end_deg - start_deg
    if segment.sweep and sweep < 0:
        sweep += 360.0
    if not segment.sweep and sweep > 0:
        sweep -= 360.0
    return ArcGeometry(center, radius, start_deg, sweep)


def sample_arc(start: Pt, segment: ArcTo) -> list[Pt]:
    """The arc as points, ending exactly on its endpoint."""
    geometry = arc_geometry(start, segment)
    steps = max(1, math.ceil(abs(geometry.sweep_deg) / SAMPLE_DEG))
    points = []
    for i in range(1, steps + 1):
        angle = math.radians(geometry.start_deg + geometry.sweep_deg * i / steps)
        points.append(
            Pt(
                geometry.center.x + geometry.radius * math.cos(angle),
                geometry.center.y + geometry.radius * math.sin(angle),
            )
        )
    points[-1] = segment.to
    return points
