"""A miniature spec set standing in for the real library.

Deliberately shaped like the models it will hold — a discriminated block
union, a nested list of objects, a fixed-length numeric tuple, closed
vocabularies and a cross-field invariant — so kernel behaviour is tested
against the shapes it actually has to support.
"""

from typing import TYPE_CHECKING, Any, Literal, Optional, Union

from physics_svg.schema import Deferred, Invalid, Number, field, spec


@spec
class Source:
    """Вложенный объект без дискриминатора — не выбор между видами блоков."""

    title: str = field(min_length=1)
    year: Optional[int] = None


@spec
class Point:
    """Точка данных."""

    x: Number
    y: Number


@spec
class Series:
    """Одна серия графика."""

    points: list[Point] = field(min_items=1, doc="Точки серии, хотя бы одна")
    label: Optional[str] = None
    style: Literal["solid", "dashed", "dotted"] = "solid"


@spec
class Graph:
    """График с осями."""

    type: Literal["graph"]
    x_label: str = field(min_length=1, doc="Подпись оси X")
    y_range: tuple[Number, Number] = field(doc="Диапазон оси Y: [min, max]")
    series: list[Series] = field(default_factory=list)
    grid: Literal["ticks", "fine"] = "ticks"
    ticks: Optional[int] = field(default=None, gt=0, le=20)
    source: Optional[Source] = field(default=None, doc="Откуда данные")

    def check(self) -> None:
        if self.y_range[0] >= self.y_range[1]:
            raise Invalid(
                f"диапазон должен быть [min, max] с min < max, получено {list(self.y_range)}",
                field="y_range",
            )


@spec
class Note:
    """Текстовая врезка."""

    type: Literal["note"]
    body: str = field(min_length=1)
    tags: dict[str, str] = field(default_factory=dict)


Block = Union[Graph, Note]


#: A container whose children are resolved at parse time, the way document
#: blocks are: the union is assembled from a registry, not written down.
if TYPE_CHECKING:
    CHILD = Any
else:
    CHILD = Deferred(lambda: Block)


@spec
class Folder:
    """Контейнер, союз детей которого разрешается при разборе."""

    type: Literal["folder"]
    children: list[CHILD] = field(min_items=1)
