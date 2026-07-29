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
from typing import Callable

from physics_svg.draw.geometry import BBox, Pt, union_all
from physics_svg.draw.nodes import Node, Rect
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


class Canvas:
    """A drawing surface for one illustration."""

    def __init__(self, scope: str = "") -> None:
        self.scope = scope
        self._nodes: list[Node] = []
        self._defs: dict[str, str] = {}

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
