"""A vector diagram: forces on a body, an addition, a decomposition.

Lengths are given **in cells**, not in pixels and not in newtons: a textbook
draws 30 N as three cells and writes "1 cell = 10 N" underneath. The renderer
picks the cell size so the picture fits; equal numbers therefore always draw
equal, which is the property a diagram of forces has to have.

Angles are the ones a student measures with a protractor: degrees
counter-clockwise from the horizontal, so 90 points up and −90 points down.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.elements import vector_sum
from physics_svg.schema import Invalid, Number, field, spec

#: Beyond this the labels of a common-origin diagram start colliding, and
#: the drawing stops being readable at the size it is printed.
MAX_VECTORS = 6

#: Length is counted in cells, so it has to stay countable.
MAX_LENGTH = 12

#: A resultant shorter than this would draw as a stub with a head.
MIN_RESULTANT = 0.15

Arrangement = Literal["common", "chain", "parallelogram"]
Body = Literal["point", "block", "ball"]


@spec
class ArrowSpec:
    """Один вектор."""

    length: Number = field(gt=0, le=MAX_LENGTH, doc="Длина в клетках")
    angle: Number = field(
        doc="Направление в градусах: 0 — вправо, 90 — вверх, −90 — вниз"
    )
    label: Optional[str] = field(default=None, doc="Подпись у наконечника: «F₁», «υ»")
    id: Optional[str] = field(default=None, doc="Нужен, только если на вектор ссылается угол")
    style: Literal["solid", "dashed"] = field(
        default="solid", doc="Пунктир — для построений: осей, проекций, направлений"
    )


@spec
class AngleSpec:
    """Дуга угла между двумя векторами."""

    between: tuple[str, str] = field(doc="Два id векторов")
    label: Optional[str] = field(default=None, doc="Подпись: «α», «30°»")


@spec
class VectorsSpec:
    """Векторная диаграмма."""

    type: Literal["vectors"]
    vectors: list[ArrowSpec] = field(min_items=1, max_items=MAX_VECTORS)
    id: Optional[str] = None
    arrangement: Arrangement = field(
        default="common",
        doc="common — все из одной точки; chain — цепочкой; parallelogram — по правилу параллелограмма",
    )
    body: Optional[Body] = field(
        default=None, doc="Тело в точке приложения; только при arrangement 'common'"
    )
    resultant: Optional[str] = field(
        default=None, doc="Подпись равнодействующей; она вычисляется сама"
    )
    grid: bool = field(default=False, doc="Клетчатый фон, чтобы длины можно было сосчитать")
    angles: list[AngleSpec] = field(default_factory=list)
    caption: Optional[str] = field(default=None, doc="Подпись под рисунком: «1 клетка = 10 Н»")

    def check(self) -> None:
        self._check_ids()
        if self.arrangement == "parallelogram" and len(self.vectors) != 2:
            raise Invalid(
                "по правилу параллелограмма складывают ровно два вектора, "
                f"получено {len(self.vectors)}",
                field="vectors",
            )
        if self.body is not None and self.arrangement != "common":
            raise Invalid(
                "тело рисуется в общей точке приложения — только при arrangement 'common'",
                field="body",
            )
        if self.resultant is not None:
            length, _ = self.sum
            if length < MIN_RESULTANT:
                raise Invalid(
                    "равнодействующая почти нулевая — рисовать нечего; "
                    "если это задача о равновесии, скажи об этом в условии, а не стрелкой",
                    field="resultant",
                )

    def _check_ids(self) -> None:
        ids = [v.id for v in self.vectors if v.id]
        if len(set(ids)) != len(ids):
            raise Invalid(f"id векторов должны быть уникальны, получено {ids}", field="vectors")
        for i, mark in enumerate(self.angles):
            first, second = mark.between
            if first == second:
                raise Invalid(f"angles[{i}]: угол между вектором и им же", field="angles")
            for reference in mark.between:
                if reference not in ids:
                    raise Invalid(
                        f"angles[{i}]: вектор с id '{reference}' не найден; "
                        f"есть {ids or 'ни одного — добавь id нужным векторам'}",
                        field="angles",
                    )

    @property
    def sum(self) -> tuple[float, float]:
        """Resultant as (length, angle). Dashed vectors are construction
        lines — axes, projections — and are not part of the sum."""
        return vector_sum(
            [(v.length, v.angle) for v in self.vectors if v.style == "solid"]
        )
