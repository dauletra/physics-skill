"""The canvas: collects nodes, resolves element ids, and emits one SVG.

Two responsibilities that used to be spread across every generator live here
instead.

**The viewBox is computed, not declared.** A generator draws in whatever
coordinates suit the object and the canvas fits the box around the result.
Nothing has to be re-measured by hand when a picture grows a label.

**Element ids are scoped.** Ids are global inside an HTML page, so two
instruments on one worksheet cannot both define `#hatch`. Every id goes
through `uid()`, which prefixes it with the canvas scope; the document layer
gives each block a distinct scope. This is what makes `<defs>`, patterns and
markers usable in the library at all — they do not have to be avoided.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable, Sequence

from physics_svg.draw.geometry import BBox, Pt, Transform, union_all
from physics_svg.draw.nodes import Group, Line, Node, Path, Rect
from physics_svg.draw.pathdata import LineTo, Move
from physics_svg.draw.style import Style
from physics_svg.draw.text import FONT_STACK, num

#: Screen pixels per user unit. Every picture in the library is calibrated to
#: this, which is what makes tick labels on a graph and on an instrument come
#: out the same physical size on the page. Changing it rescales the whole
#: library at once — that is the point of having it in exactly one place.
SCREEN_SCALE = 1.5

#: Default slack around the content box, in user units. Strokes are centred
#: on their path, so a contour drawn exactly on the edge would be clipped in
#: half without this.
DEFAULT_PADDING = 1.0

#: viewBox bounds are snapped outward to this grid, so that a one-unit change
#: in a label estimate does not churn the golden files.
_SNAP = 0.5


@dataclass(frozen=True)
class Tiling:
    """A repeating cell — an exercise-book square, a millimetre grid.

    One declaration, two renderings: SVG registers it as a `<pattern>` and
    fills a rectangle with it, a backend of native shapes repeats the cell
    across the area as ordinary lines. Stating it once is what keeps the two
    from drifting; a pattern written as markup could only ever be one of them.

    `base` is a tiling the cell is laid over — the millimetre paper, whose
    centimetre square is filled with the fine one.
    """

    id: str
    step_x: float
    step_y: float
    tile: tuple[Node, ...]
    base: "Tiling | None" = None

    def __str__(self) -> str:
        """A fill value: `url(#…)`, exactly what a style already holds."""
        return f"url(#{self.id})"

    def expanded(self, region: BBox) -> list[Node]:
        """The cell repeated across `region`, as plain nodes.

        The area is always a whole number of cells (a ruling is measured in
        its own cells), so nothing has to be clipped.

        **A cell edge becomes one line across the field.** Repeating the cell
        literally is quadratic — a millimetre field of a hundred by sixty
        cells would be six thousand shapes — while the squares it draws are
        really a few hundred straight lines. Anything that is not an edge (the
        dot of a dotted ruling) is repeated cell by cell, because there is
        nothing to join it into.
        """
        nodes: list[Node] = []
        if self.base is not None:
            nodes.extend(self.base.expanded(region))
        columns = max(1, round(region.width / self.step_x))
        rows = max(1, round(region.height / self.step_y))
        for child in self.tile:
            spans, rest = self._split(child)
            for offset, horizontal, style in spans:
                nodes.extend(self._ruled(region, offset, horizontal, style, columns, rows))
            for row in range(rows):
                for column in range(columns):
                    shift = Transform.translate(
                        region.x0 + column * self.step_x, region.y0 + row * self.step_y
                    )
                    nodes.extend(node.transformed(shift) for node in rest)
        return nodes

    def _split(self, child: Node) -> tuple[list[tuple[float, bool, Style]], list[Node]]:
        """Cell edges (offset, horizontal?, style) apart from everything else."""
        if not isinstance(child, (Line, Path)):
            return [], [child]
        pairs = _straight_pairs(child)
        if pairs is None:
            return [], [child]
        spans: list[tuple[float, bool, Style]] = []
        leftovers: list[Node] = []
        for a, b in pairs:
            if a.y == b.y and sorted((a.x, b.x)) == [0.0, self.step_x]:
                spans.append((a.y, True, child.style))
            elif a.x == b.x and sorted((a.y, b.y)) == [0.0, self.step_y]:
                spans.append((a.x, False, child.style))
            else:
                leftovers.append(Line(a, b, child.style))
        return spans, leftovers

    def _ruled(
        self,
        region: BBox,
        offset: float,
        horizontal: bool,
        style: Style,
        columns: int,
        rows: int,
    ) -> list[Node]:
        if horizontal:
            return [
                Line(
                    Pt(region.x0, region.y0 + row * self.step_y + offset),
                    Pt(region.x1, region.y0 + row * self.step_y + offset),
                    style,
                )
                for row in range(rows)
            ]
        return [
            Line(
                Pt(region.x0 + column * self.step_x + offset, region.y0),
                Pt(region.x0 + column * self.step_x + offset, region.y1),
                style,
            )
            for column in range(columns)
        ]


class Canvas:
    """A drawing surface for one illustration."""

    def __init__(self, scope: str = "") -> None:
        self.scope = scope
        self._nodes: list[Node] = []
        self._defs: dict[str, str] = {}
        self._tilings: dict[str, Tiling] = {}

    # --- building -------------------------------------------------------

    def add(self, *nodes: Node) -> None:
        self._nodes.extend(nodes)

    def extend(self, nodes: list[Node]) -> None:
        self._nodes.extend(nodes)

    def uid(self, name: str) -> str:
        """Element id, unique across the page the canvas will be embedded in."""
        return f"{self.scope}-{name}" if self.scope else name

    def define(self, name: str, build: Callable[[str], str]) -> str:
        """Register a `<defs>` entry and get back its id.

        `build` receives the resolved id so the markup can reference itself.
        Registering the same name twice keeps the first definition: identical
        names are expected to mean identical content (a grid pattern shared by
        two equal fields), so the id is the cache key.
        """
        element_id = self.uid(name)
        if element_id not in self._defs:
            self._defs[element_id] = build(element_id)
        return element_id

    def tiling(
        self,
        name: str,
        step_x: float,
        step_y: float,
        tile: Sequence[Node],
        base: "Tiling | None" = None,
    ) -> Tiling:
        """Register a repeating cell and get it back to fill with."""
        entry = Tiling(self.uid(name), step_x, step_y, tuple(tile), base)
        self._tilings[entry.id] = entry
        self.define(name, lambda pid: _pattern(entry))
        return entry

    def fill_tiled(self, region: BBox, tiling: Tiling) -> Node:
        """The area, filled with the cell."""
        return Rect(
            Pt(region.x0, region.y0),
            region.width,
            region.height,
            Style(fill=str(tiling)),
        )

    @property
    def nodes(self) -> list[Node]:
        """Everything drawn, in order."""
        return list(self._nodes)

    def flat_nodes(self) -> list[Node]:
        """The same, with groups flattened and tiled areas turned into lines.

        What a backend without patterns and without nested frames can draw —
        which is every backend except SVG.
        """
        flat: list[Node] = []
        for node in self._nodes:
            if isinstance(node, Group):
                flat.extend(node.flattened())
                continue
            tiling = self._tiling_of(node)
            if tiling is not None:
                box = node.bbox()
                assert box is not None
                flat.extend(tiling.expanded(box))
                continue
            flat.append(node)
        return flat

    def _tiling_of(self, node: Node) -> Tiling | None:
        fill = getattr(getattr(node, "style", None), "fill", None)
        if not isinstance(fill, str) or not fill.startswith("url(#"):
            return None
        return self._tilings.get(fill[5:-1])

    @property
    def is_empty(self) -> bool:
        return not self._nodes

    # --- measuring ------------------------------------------------------

    def content_box(self) -> BBox | None:
        """Extent of everything drawn, in user units."""
        return union_all(node.bbox() for node in self._nodes)

    # --- emitting -------------------------------------------------------

    def render(
        self,
        *,
        viewbox: BBox | None = None,
        padding: float = DEFAULT_PADDING,
        scale: float = SCREEN_SCALE,
        css_class: str = "visual-svg",
        sized: bool = False,
        background: str | None = None,
        fluid_height: float | None = None,
    ) -> str:
        """Serialise to one `<svg>` element.

        `viewbox`   pin the box explicitly instead of fitting the content.
        `sized`     emit `width`/`height` in px — required for a standalone
                    file, omitted inside the document where CSS sets the size.
        `background`fill the whole box (a standalone file must carry its own
                    white paper; inside the document the page provides it).
        `fluid_height`
                    stretch to the container width at this fixed pixel
                    height, for rulings that have no horizontal geometry.
        """
        box = self._resolve_box(viewbox, padding)
        if fluid_height is not None:
            # Marks the one case where the height attribute must survive the
            # page stylesheet: a stretched ruling has no intrinsic ratio.
            css_class = f"{css_class} visual-fluid"
        parts = [
            f'<svg class="{css_class}" xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{num(box.x0)} {num(box.y0)} {num(box.width)} {num(box.height)}" '
            f'font-family="{FONT_STACK}"'
        ]
        if fluid_height is not None:
            parts.append(f' width="100%" height="{num(fluid_height)}" preserveAspectRatio="none"')
        elif sized:
            parts.append(f' width="{num(box.width * scale)}" height="{num(box.height * scale)}"')
        parts.append(">")
        if self._defs:
            parts.append("<defs>" + "".join(self._defs[key] for key in self._defs) + "</defs>")
        if background is not None:
            parts.append(
                Rect(
                    Pt(box.x0, box.y0), box.width, box.height, Style(fill=background)
                ).svg()
            )
        parts.extend(node.svg() for node in self._nodes)
        parts.append("</svg>")
        return "".join(parts)

    def frame_box(self, viewbox: BBox | None = None, padding: float = DEFAULT_PADDING) -> BBox:
        """The box the picture is framed by — the `viewBox` of the SVG, and
        the extent a Word drawing is sized from."""
        return self._resolve_box(viewbox, padding)

    def _resolve_box(self, viewbox: BBox | None, padding: float) -> BBox:
        if viewbox is not None:
            return viewbox
        content = self.content_box()
        if content is None:
            # An empty canvas is a generator bug, not author data; give it a
            # degenerate but valid box rather than emitting broken markup.
            return BBox(0.0, 0.0, 1.0, 1.0)
        return _snap_out(content.expanded(padding))


def _snap_out(box: BBox) -> BBox:
    return BBox(
        math.floor(box.x0 / _SNAP) * _SNAP,
        math.floor(box.y0 / _SNAP) * _SNAP,
        math.ceil(box.x1 / _SNAP) * _SNAP,
        math.ceil(box.y1 / _SNAP) * _SNAP,
    )


def _pattern(tiling: Tiling) -> str:
    """The tiling as an SVG `<pattern>`.

    The cell is serialised from its own nodes, so the two renderings cannot
    describe different rulings. A tiling laid over another one opens with a
    rectangle filled by it — the nesting keeps the markup small however large
    the field is.
    """
    base = (
        f'<rect width="{num(tiling.step_x)}" height="{num(tiling.step_y)}" '
        f'fill="{tiling.base}"/>'
        if tiling.base is not None
        else ""
    )
    cell = "".join(node.svg() for node in tiling.tile)
    return (
        f'<pattern id="{tiling.id}" width="{num(tiling.step_x)}" '
        f'height="{num(tiling.step_y)}" patternUnits="userSpaceOnUse">'
        f"{base}{cell}</pattern>"
    )


def _straight_pairs(child: Line | Path) -> list[tuple[Pt, Pt]] | None:
    """The node as straight segments, or `None` if it is not made of them."""
    if isinstance(child, Line):
        return [(child.a, child.b)]
    pairs: list[tuple[Pt, Pt]] = []
    here: Pt | None = None
    for segment in child.segments():
        if isinstance(segment, Move):
            here = segment.to
        elif isinstance(segment, LineTo):
            if here is None:
                return None
            pairs.append((here, segment.to))
            here = segment.to
        else:
            return None
    return pairs
