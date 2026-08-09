"""The registry of illustration types.

One package per type, self-registering on import. A type declares its spec,
its renderer and the directory holding its example specs and documentation;
everything else in the project — the JSON Schema, the gallery, the golden
tests, the reference shipped with the skill, the example library the model
picks from — is derived from that declaration.

The consequence worth protecting: adding an illustration should be adding a
directory, never editing a list somewhere else. `tests/test_conformance.py`
enforces the other half — that a registered type actually carries the specs
and documentation it promises.
"""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Union

from physics_svg.draw import BOARD, DEFAULT_PADDING, SCREEN_SCALE, WHITE, BBox, Canvas
from physics_svg.draw.nodes import Group, Node, Text
from physics_svg.draw.shapes import EMU_PER_PX, Frame, SlideDrawing, WordDrawing
from physics_svg.schema import parse

#: EMU per user unit at the size the library is calibrated to. The picture is
#: the same physical size in Word as on screen — one calibration, two formats.
EMU_PER_UNIT = SCREEN_SCALE * EMU_PER_PX


@dataclass(frozen=True)
class Layout:
    """How a type wants its canvas framed. Returned by a renderer that needs
    something other than "fit the content"."""

    padding: float = DEFAULT_PADDING
    #: Pin the frame instead of fitting the content.
    viewbox: BBox | None = None
    #: Stretch to the container width at this pixel height. Only meaningful
    #: inside a document; a standalone file is always sized from its content.
    fluid_height: float | None = None


Renderer = Callable[[Any, Canvas], Union[Layout, None]]


@dataclass(frozen=True)
class VisualType:
    #: Value of the `type` field in JSON.
    tag: str
    #: Human name, used by the gallery and the generated reference.
    title: str
    model: type
    render: Renderer
    #: The type's package directory: specs/, doc.md, card.md live here.
    directory: Path

    @property
    def specs(self) -> list[Path]:
        return sorted((self.directory / "specs").glob("*.json"))

    def doc(self, name: str) -> Path:
        return self.directory / name


_REGISTRY: dict[str, VisualType] = {}
_LOADED = False


def register(*, tag: str, title: str, model: type, render: Renderer, module: str) -> None:
    """Called by a type package at import time."""
    if tag in _REGISTRY:
        raise RuntimeError(f"visual type {tag!r} is already registered")
    directory = Path(importlib.import_module(module).__file__ or "").parent
    _REGISTRY[tag] = VisualType(tag, title, model, render, directory)


def load_all() -> dict[str, VisualType]:
    """Import every type package once, then hand back the registry."""
    global _LOADED
    if not _LOADED:
        package = importlib.import_module("physics_svg.visuals")
        for info in pkgutil.iter_modules(package.__path__):
            if info.ispkg:
                importlib.import_module(f"physics_svg.visuals.{info.name}")
        _LOADED = True
    return dict(sorted(_REGISTRY.items()))


def visual_type(tag: str) -> VisualType:
    return load_all()[tag]


def visual_annotation() -> Any:
    """Union of every registered spec — the annotation a visual is parsed
    against, assembled at runtime so no list has to be maintained by hand."""
    models = tuple(entry.model for entry in load_all().values())
    if not models:
        raise RuntimeError("no visual types registered")
    return Union[models]


def parse_visual(data: object, name: str = "") -> Any:
    """Validate one visual spec — the same schema whether it stands alone or
    sits inside a document."""
    return parse(visual_annotation(), data, name=name)


def render_to_canvas(model: Any, canvas: Canvas) -> Layout:
    entry = load_all()[getattr(model, "type")]
    return entry.render(model, canvas) or Layout()


def build_svg(
    model: Any,
    *,
    scope: str = "",
    standalone: bool = False,
    scale: float = SCREEN_SCALE,
) -> str:
    """Render one visual to SVG.

    `standalone` produces a file that can be dropped into a presentation: it
    carries its own white paper. Inside a document the page provides that,
    and a fluid type may stretch to the column. Sizing is emitted either way
    — the frame is known exactly, so the document CSS only has to cap it.
    """
    canvas = Canvas(scope)
    layout = render_to_canvas(model, canvas)
    return canvas.render(
        viewbox=layout.viewbox,
        padding=layout.padding,
        scale=scale,
        sized=True,
        background=WHITE if standalone else None,
        fluid_height=None if standalone else layout.fluid_height,
    )


def build_shapes(model: Any, *, width_emu: int) -> tuple[str, int, int]:
    """Render one visual to native Word shapes: (group, width, height) in EMU.

    Same renderer, same canvas, same frame as the SVG — only the serialiser
    differs, which is what keeps a picture identical in the two formats.

    `width_emu` is the room the picture has across. Two things depend on it:
    a drawing wider than the column is fitted into it whole (the counterpart
    of `max-width: 100%`), and a ruling with no width of its own stretches to
    fill it, keeping the height its author asked for — which is exactly what
    `preserveAspectRatio="none"` does on the page.
    """
    canvas = Canvas()
    layout = render_to_canvas(model, canvas)
    box = canvas.frame_box(layout.viewbox, layout.padding)
    if layout.fluid_height is not None:
        sx, sy = width_emu / box.width, EMU_PER_UNIT
    else:
        needed = box.width * EMU_PER_UNIT
        factor = min(1.0, width_emu / needed) if needed else 1.0
        sx = sy = EMU_PER_UNIT * factor
    frame = Frame(box, sx, sy)
    drawing = WordDrawing(frame)
    return drawing.group(canvas.flat_nodes()), frame.width, frame.height


def label_metrics(model: Any) -> tuple[float, float, float]:
    """The picture as a slide has to reason about it: (smallest label, width,
    height) in user units, on the board scale.

    A slide chooses where to put an illustration by whether its labels will
    be legible there, and that question cannot be answered without drawing
    the picture first — the frame grows with the labels. So the picture is
    drawn, measured and thrown away; it costs one render and it replaces a
    rule that would otherwise be guessed (docs/pptx.md §6.3).
    """
    canvas = Canvas(medium=BOARD)
    layout = render_to_canvas(model, canvas)
    box = canvas.frame_box(layout.viewbox, layout.padding)
    sizes = [node.size for node in _labels(canvas.flat_nodes())]
    return (min(sizes) if sizes else 0.0), box.width, box.height


def _labels(nodes: Iterable[Node]) -> Iterator[Text]:
    for node in nodes:
        if isinstance(node, Group):
            yield from _labels(node.flattened())
        elif isinstance(node, Text):
            yield node


def build_slide_shapes(model: Any, *, width_emu: int, height_emu: int) -> tuple[str, int, int]:
    """Render one visual as shapes on a slide: (group, width, height) in EMU.

    Two things differ from the Word path, and both follow from where the
    picture is going.

    **It is fitted into a box, not into a column.** A sheet gives a picture
    its width and as much height as it needs; a slide gives it a rectangle,
    and the picture takes the smaller of the two ratios so that it fits
    whole. The print calibration does not apply — on a board the picture is
    as large as the room it is given, not 1,5 px per unit.

    **It is drawn on the board medium.** The labels are set at the scale a
    class reads from seven metres, which is the whole of
    docs/visual-scale.md: the same drawing, a different label scale.
    """
    canvas = Canvas(medium=BOARD)
    layout = render_to_canvas(model, canvas)
    box = canvas.frame_box(layout.viewbox, layout.padding)
    scale = min(width_emu / box.width, height_emu / box.height)
    frame = Frame(box, scale, scale)
    drawing = SlideDrawing(frame)
    return drawing.group(canvas.flat_nodes()), frame.width, frame.height
