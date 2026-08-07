"""Emitting a presentation: the canonical JSON, and the page around it.

Two artefacts from one source (docs/presentation.md §2). `build_data` turns
the validated models into the wire contract — `format`, `title`, `slides`,
with author text parsed into runs and visuals rendered to SVG. `build_page`
takes that data and performs **exactly one substitution** in the player
template: it injects the JSON blob. Nothing else: the player renders slides
from the blob at runtime, Python never writes slide markup, and that is
what keeps today's single file and tomorrow's server showing the same
lesson from the same data.

The blob is extractable by design — `extract_data` is the inverse the
tests hold as an invariant, and the future migration path for files that
have already reached teachers.
"""

from __future__ import annotations

import dataclasses
import json
import re
from pathlib import Path
from typing import Any

from physics_svg.draw import SCREEN_SCALE, Canvas
from physics_svg.inline import parse_inline, runs_json
from physics_svg.presentation.manifest import PresentationSpec
from physics_svg.presentation.slides.registry import load_all
from physics_svg.visuals import render_to_canvas

#: Version of the wire contract. Grows only on a breaking change of the
#: JSON's shape — never on a new slide type, which an older player must
#: survive with a placeholder rather than a failure.
FORMAT = 1

_PLAYER = Path(__file__).parent / "player" / "player.html"
_MARKER = "__PRESENTATION_DATA__"
_DATA_BLOCK = re.compile(
    r'<script type="application/json" id="presentation-data">(.*?)</script>', re.S
)


# --- helpers for the slide emitters --------------------------------------


def runs(text: object) -> list[dict[str, Any]]:
    """Author text as wire runs — the JSON form declared in `physics_svg.inline`."""
    return runs_json(parse_inline(text))


def emit_visual(model: Any, scope: str) -> dict[str, Any]:
    """An illustration as the wire carries it: the spec to re-render from,
    the SVG to show, and the frame to reserve before the SVG arrives.

    Same renderer, same canvas, same frame as everywhere else — only the
    destination differs, which is what keeps a picture identical on a
    slide, on a sheet and in Word.
    """
    canvas = Canvas(scope)
    layout = render_to_canvas(model, canvas)
    box = canvas.frame_box(layout.viewbox, layout.padding)
    svg = canvas.render(
        viewbox=layout.viewbox,
        padding=layout.padding,
        sized=True,
        fluid_height=layout.fluid_height,
    )
    height = layout.fluid_height if layout.fluid_height is not None else box.height * SCREEN_SCALE
    return {
        "spec": _spec_data(model),
        "svg": svg,
        "width": round(box.width * SCREEN_SCALE),
        "height": round(height),
    }


def _spec_data(model: Any) -> Any:
    """The visual's spec back as plain JSON data.

    Fields left at None are dropped — absent and default-None are the same
    spec, and the wire should carry what distinguishes this picture, not
    the whole questionnaire. The result validates like any author spec,
    which is what lets a server re-render or edit the picture later.
    """

    def strip(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: strip(item) for key, item in value.items() if item is not None}
        if isinstance(value, (list, tuple)):
            return [strip(item) for item in value]
        return value

    return strip(dataclasses.asdict(model))


# --- the two artefacts ----------------------------------------------------


def build_data(presentation: PresentationSpec, slides: list[Any]) -> dict[str, Any]:
    """The canonical `presentation.json` as data."""
    registry = load_all()
    emitted = [
        registry[model.type].emit(model, f"s{index + 1}") for index, model in enumerate(slides)
    ]
    return {"format": FORMAT, "title": presentation.title, "slides": emitted}


def data_json(data: dict[str, Any]) -> str:
    """The canonical file: readable, stable, diffable."""
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def build_page(data: dict[str, Any]) -> str:
    """The player template with the blob injected — the one substitution."""
    template = _PLAYER.read_text(encoding="utf-8")
    if template.count(_MARKER) != 1:
        raise RuntimeError(
            f"в шаблоне плеера точка вставки {_MARKER} должна встречаться ровно один раз"
        )
    return template.replace(_MARKER, _safe_json(data))


def _safe_json(data: dict[str, Any]) -> str:
    """The blob as it sits inside `<script>`.

    A literal `</` in author text would end the data block early — the same
    class of problem `draw.clean` and the XML gate solve for the other
    outputs. `<\\/` is the standard JSON escape for the same character, so
    the blob stays valid JSON and the page stays whole.
    """
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/")


def extract_data(page: str) -> Any:
    """The blob back out of a built page — the invariant, and the migration
    path for files already in teachers' hands."""
    found = _DATA_BLOCK.search(page)
    if found is None:
        raise ValueError("на странице нет блока presentation-data")
    return json.loads(found.group(1))
