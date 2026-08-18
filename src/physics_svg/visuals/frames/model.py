"""One motion seen from two frames of reference.

The author describes the motion **in the frame of the carrier** — the simple
half of the picture, the one a passenger sees — and how far the carrier
travels meanwhile. The second frame is not authored: every position of the
body is displaced by `shift·t`, which is the Galilean transform written out,
and the parabola of a ball thrown in a moving carriage comes out as a result
rather than as a curve somebody named.

That is also why `motion` is a law of motion and not a shape. The marks of a
stroboscopic trail stand at equal *times*; a toss crowds them near the top,
and it is exactly that crowding which makes the transformed trail a parabola.
Spaced evenly along the same segment they would transform into a triangle —
a picture that contradicts the topic it is drawn for.

Lengths are in cells, as on a vector diagram: the renderer picks the cell
size, and «1 cell = 1 m» is the caption's business.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.schema import Invalid, Number, field, spec

#: Bounds of countability, the same reasoning as `vectors.MAX_LENGTH`: a
#: length nobody can count off the grid is not a length on a diagram.
MAX_RISE = 12.0
MAX_TRAVEL = 12.0
MAX_SHIFT = 20.0

#: Fewer than three marks do not read as a row of positions; more than a
#: dozen merge into the line through them.
MIN_MARKS = 3
MAX_MARKS = 12

Motion = Literal["still", "uniform", "toss", "drop"]

#: Which extra field each law of motion needs — and, read the other way, which
#: fields are meaningless with it. The message of a wrong combination comes
#: from here, so the table is the single statement of the rule.
NEEDS: dict[str, str] = {
    "still": "",
    "uniform": "travel",
    "toss": "rise",
    "drop": "rise",
}


@spec
class FramesSpec:
    """Одно движение в двух системах отсчёта."""

    type: Literal["frames"]
    motion: Motion = field(
        doc="Движение тела в системе носителя: still — покоится, uniform — равномерно, "
        "toss — брошено вверх и вернулось, drop — падает"
    )
    shift: Number = field(
        ge=-MAX_SHIFT,
        le=MAX_SHIFT,
        doc="Сколько клеток проезжает носитель за то же время; знак задаёт сторону",
    )
    carrier: str = field(min_length=1, doc="Подпись первого кадра: «вагон», «самолёт», «тележка»")
    ground: str = field(min_length=1, doc="Подпись второго кадра: «земля», «дорога», «перрон»")
    id: Optional[str] = None
    travel: Optional[tuple[Number, Number]] = field(
        default=None, doc="Только для uniform: смещение тела в своём кадре, [по x, по y] в клетках"
    )
    rise: Optional[Number] = field(
        default=None, doc="Только для toss и drop: высота подъёма или падения, в клетках"
    )
    marks: int = field(
        default=5,
        ge=MIN_MARKS,
        le=MAX_MARKS,
        doc="Сколько положений тела показать; промежутки времени между ними равны",
    )
    grid: bool = field(default=False, doc="Клетчатый фон, чтобы длины можно было сосчитать")
    axes: bool = field(
        default=False,
        doc="Оси x и y каждой системы отсчёта из её начала — точки, где тело было в начале",
    )
    caption: Optional[str] = field(default=None, doc="Подпись под рисунком: «1 клетка = 1 м»")

    def check(self) -> None:
        if self.shift == 0:
            raise Invalid(
                "носитель не движется относительно второй системы отсчёта — кадры выйдут "
                "одинаковыми; если задача про покой, это одна картинка, а не две",
                field="shift",
            )
        self._check_motion_fields()
        if self.motion == "uniform":
            assert self.travel is not None
            if self.travel == (0, 0):
                raise Invalid(
                    "равномерное движение без смещения — это motion 'still'",
                    field="travel",
                )
            for axis, value in zip(("x", "y"), self.travel):
                if abs(value) > MAX_TRAVEL:
                    raise Invalid(
                        f"смещение по {axis} — {value} клеток при пределе {MAX_TRAVEL:g}",
                        field="travel",
                    )
        if self.rise is not None and not 0 < self.rise <= MAX_RISE:
            raise Invalid(
                f"высота — от 0 до {MAX_RISE:g} клеток, получено {self.rise}", field="rise"
            )

    def _check_motion_fields(self) -> None:
        needed = NEEDS[self.motion]
        for name in ("travel", "rise"):
            given = getattr(self, name) is not None
            if name == needed and not given:
                raise Invalid(
                    f"движению '{self.motion}' нужно поле '{name}'",
                    field=name,
                )
            if name != needed and given:
                wanted = f"поле '{needed}'" if needed else "только shift"
                raise Invalid(
                    f"поле '{name}' к движению '{self.motion}' не относится; "
                    f"ему нужно {wanted}",
                    field=name,
                )

    @property
    def positions(self) -> list[tuple[float, float]]:
        """Where the body is, in the carrier's frame, at `marks` equal times.

        Cells, y upwards, the body starting at the origin. The carrier and
        the ground are drawn around this; the second frame is this list plus
        `shift·t`.
        """
        return [self._at(step / (self.marks - 1)) for step in range(self.marks)]

    def _at(self, t: float) -> tuple[float, float]:
        if self.motion == "uniform":
            assert self.travel is not None
            return self.travel[0] * t, self.travel[1] * t
        if self.motion == "toss":
            assert self.rise is not None
            # Up and back down: the parabola of a throw, at equal times.
            return 0.0, 4.0 * self.rise * t * (1.0 - t)
        if self.motion == "drop":
            assert self.rise is not None
            return 0.0, -self.rise * t * t
        return 0.0, 0.0
