"""Ruled writing area — the place a student works.

A pure illustration: it knows nothing about the question next to it. What is
done on the paper is said by the neighbouring question, which is why there
is no `answer` field here and never will be.
"""

from __future__ import annotations

from typing import Literal, Optional

from physics_svg.schema import Invalid, field, spec

Ruling = Literal["lines", "grid", "mm", "dots", "plain"]

#: Ruling pitch in user units. For `mm` this is the **centimetre** square:
#: `rows`/`cols` are always counted in the ruling's large cell, so "graph
#: paper 12x12" means 12x12 cm rather than 12x12 mm.
STEPS: dict[str, int] = {"lines": 18, "plain": 18, "grid": 12, "dots": 12, "mm": 30}

#: Rulings with a square cell cannot be stretched to the column width
#: without turning the square into a rectangle, so their width is explicit.
SQUARE_RULINGS = frozenset({"grid", "dots", "mm"})

#: Document column width in user units, and the height limit of one field
#: (about two screens). Wider than the column would overflow the page;
#: taller than the limit is almost certainly a mistake in the unit of `rows`.
COLUMN_WIDTH = 490
MAX_HEIGHT = 900


@spec
class PaperSpec:
    """Разлинованное поле для работы ученика."""

    type: Literal["paper"]
    rows: int = field(
        gt=0, doc="Высота поля в строках/клетках самой разлиновки, а не в пикселях"
    )
    id: Optional[str] = None
    ruling: Ruling = "lines"
    cols: Optional[int] = field(
        default=None,
        gt=0,
        doc="Ширина в клетках; обязательна для клетчатых разлиновок, "
        "без неё поле тянется на всю колонку",
    )

    @property
    def step(self) -> int:
        return STEPS[self.ruling]

    @property
    def width(self) -> float:
        return self.cols * self.step if self.cols is not None else COLUMN_WIDTH

    @property
    def height(self) -> float:
        return self.rows * self.step

    def check(self) -> None:
        if self.cols is None and self.ruling in SQUARE_RULINGS:
            raise Invalid(
                f"разлиновке '{self.ruling}' нужно поле 'cols': квадратную клетку "
                "нельзя растянуть по ширине колонки",
                field="cols",
            )
        if self.cols is not None and self.width > COLUMN_WIDTH:
            raise Invalid(
                f"поле шире колонки страницы: для разлиновки '{self.ruling}' "
                f"допустимо не больше {COLUMN_WIDTH // self.step} клеток",
                field="cols",
            )
        if self.height > MAX_HEIGHT:
            raise Invalid(
                f"поле слишком высокое: для разлиновки '{self.ruling}' допустимо "
                f"не больше {MAX_HEIGHT // self.step} строк",
                field="rows",
            )
