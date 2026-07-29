"""Plane geometry: points, bounding boxes, affine transforms.

Pure data — nothing here emits SVG.

Orientation: coordinates are SVG user units, so **y grows downward**. Angles
are degrees and are measured the way a physics textbook measures them —
counter-clockwise from the positive x axis — which `polar()` converts to the
screen frame by negating the y component. Callers should never do that
negation themselves; if a generator computes `cy - r * sin(a)` inline, it is
reimplementing this module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, NamedTuple


class Pt(NamedTuple):
    """A point (or a vector — the distinction is in usage, not in type)."""

    x: float
    y: float

    def __add__(self, other: "Pt") -> "Pt":  # type: ignore[override]
        return Pt(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Pt") -> "Pt":
        return Pt(self.x - other.x, self.y - other.y)

    def __neg__(self) -> "Pt":
        return Pt(-self.x, -self.y)

    def __mul__(self, k: float) -> "Pt":  # type: ignore[override]
        return Pt(self.x * k, self.y * k)

    def __rmul__(self, k: float) -> "Pt":  # type: ignore[override]
        return Pt(self.x * k, self.y * k)

    def shifted(self, dx: float = 0.0, dy: float = 0.0) -> "Pt":
        return Pt(self.x + dx, self.y + dy)

    def length(self) -> float:
        return math.hypot(self.x, self.y)

    def distance_to(self, other: "Pt") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def normalized(self) -> "Pt":
        n = self.length()
        return Pt(0.0, 0.0) if n == 0 else Pt(self.x / n, self.y / n)

    def perpendicular(self) -> "Pt":
        """Left normal in screen terms (x, y) -> (y, -x)."""
        return Pt(self.y, -self.x)

    def angle(self) -> float:
        """Direction in textbook degrees (counter-clockwise, y up)."""
        return math.degrees(math.atan2(-self.y, self.x))

    def lerp(self, other: "Pt", t: float) -> "Pt":
        return Pt(self.x + (other.x - self.x) * t, self.y + (other.y - self.y) * t)


ORIGIN = Pt(0.0, 0.0)


def polar(center: Pt, radius: float, angle_deg: float) -> Pt:
    """Point at `radius` from `center` in the direction `angle_deg`.

    Textbook orientation: 0 deg points right, 90 deg points up the screen.
    """
    a = math.radians(angle_deg)
    return Pt(center.x + radius * math.cos(a), center.y - radius * math.sin(a))


def direction(angle_deg: float) -> Pt:
    """Unit vector for a textbook angle."""
    return polar(ORIGIN, 1.0, angle_deg)


def angle_between(a: Pt, b: Pt) -> float:
    """Signed angle from vector `a` to vector `b`, in (-180, 180] degrees."""
    delta = b.angle() - a.angle()
    return (delta + 180.0) % 360.0 - 180.0


@dataclass(frozen=True)
class BBox:
    """Axis-aligned bounding box. `x0 <= x1` and `y0 <= y1` always hold."""

    x0: float
    y0: float
    x1: float
    y1: float

    @staticmethod
    def of(points: Iterable[Pt]) -> "BBox | None":
        xs: list[float] = []
        ys: list[float] = []
        for p in points:
            xs.append(p.x)
            ys.append(p.y)
        if not xs:
            return None
        return BBox(min(xs), min(ys), max(xs), max(ys))

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def center(self) -> Pt:
        return Pt((self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2)

    @property
    def corners(self) -> tuple[Pt, Pt, Pt, Pt]:
        return (
            Pt(self.x0, self.y0),
            Pt(self.x1, self.y0),
            Pt(self.x1, self.y1),
            Pt(self.x0, self.y1),
        )

    def union(self, other: "BBox | None") -> "BBox":
        if other is None:
            return self
        return BBox(
            min(self.x0, other.x0),
            min(self.y0, other.y0),
            max(self.x1, other.x1),
            max(self.y1, other.y1),
        )

    def expanded(self, pad: float) -> "BBox":
        return BBox(self.x0 - pad, self.y0 - pad, self.x1 + pad, self.y1 + pad)

    def contains(self, other: "BBox", tolerance: float = 1e-9) -> bool:
        return (
            self.x0 <= other.x0 + tolerance
            and self.y0 <= other.y0 + tolerance
            and self.x1 >= other.x1 - tolerance
            and self.y1 >= other.y1 - tolerance
        )


def union_all(boxes: Iterable[BBox | None]) -> BBox | None:
    result: BBox | None = None
    for box in boxes:
        if box is None:
            continue
        result = box if result is None else result.union(box)
    return result


@dataclass(frozen=True)
class Transform:
    """Affine transform, stored exactly as SVG `matrix(a b c d e f)`:

        x' = a*x + c*y + e
        y' = b*x + d*y + f
    """

    a: float = 1.0
    b: float = 0.0
    c: float = 0.0
    d: float = 1.0
    e: float = 0.0
    f: float = 0.0

    @staticmethod
    def translate(dx: float, dy: float = 0.0) -> "Transform":
        return Transform(e=dx, f=dy)

    @staticmethod
    def scale(kx: float, ky: float | None = None) -> "Transform":
        return Transform(a=kx, d=kx if ky is None else ky)

    @staticmethod
    def rotate(angle_deg: float, about: Pt = ORIGIN) -> "Transform":
        """Rotation by a textbook angle (counter-clockwise on screen)."""
        a = math.radians(-angle_deg)  # SVG rotates clockwise for positive angles
        cos, sin = math.cos(a), math.sin(a)
        rot = Transform(a=cos, b=sin, c=-sin, d=cos)
        if about == ORIGIN:
            return rot
        return (
            Transform.translate(-about.x, -about.y)
            .then(rot)
            .then(Transform.translate(about.x, about.y))
        )

    def then(self, outer: "Transform") -> "Transform":
        """Self first, then `outer` — i.e. the matrix product `outer @ self`."""
        return Transform(
            a=outer.a * self.a + outer.c * self.b,
            b=outer.b * self.a + outer.d * self.b,
            c=outer.a * self.c + outer.c * self.d,
            d=outer.b * self.c + outer.d * self.d,
            e=outer.a * self.e + outer.c * self.f + outer.e,
            f=outer.b * self.e + outer.d * self.f + outer.f,
        )

    def apply(self, p: Pt) -> Pt:
        return Pt(self.a * p.x + self.c * p.y + self.e, self.b * p.x + self.d * p.y + self.f)

    def apply_box(self, box: BBox | None) -> BBox | None:
        if box is None:
            return None
        return BBox.of(self.apply(corner) for corner in box.corners)

    @property
    def is_identity(self) -> bool:
        return self == IDENTITY


IDENTITY = Transform()
