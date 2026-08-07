"""The presentation layer: slides for a lesson, shown by the player.

The artefact is a **presentation** — the sequence that leads a lesson: the
topic, the objectives, the explanation, tasks for the board, reflection. It
is a genre beside the document, not a mode of it: the two share
illustrations, author-text conventions and the validation kernel, and
nothing else. The full design is docs/presentation.md.

Python validates the draft and emits data; slides are rendered by the
HTML-JS player in the browser. That boundary is what lets the player move
to a server later without the data noticing.
"""

from physics_svg.presentation.emit import (
    FORMAT,
    build_data,
    build_page,
    data_json,
    extract_data,
)
from physics_svg.presentation.manifest import (
    PresentationSpec,
    parse_presentation,
    parse_slide,
)
from physics_svg.presentation.slides import slide_annotation
from physics_svg.presentation.workspace import Workspace, WorkspaceError, load_workspace

__all__ = [
    "FORMAT",
    "PresentationSpec",
    "Workspace",
    "WorkspaceError",
    "build_data",
    "build_page",
    "data_json",
    "extract_data",
    "load_workspace",
    "parse_presentation",
    "parse_slide",
    "slide_annotation",
]
