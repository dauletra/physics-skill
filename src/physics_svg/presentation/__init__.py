"""The presentation layer: the slides that lead a lesson.

The artefact is a **presentation** — the sequence that leads a lesson: the
topic, the objectives, the explanation, tasks for the board, reflection. It
is a genre beside the document, not a mode of it: the two share
illustrations, author-text conventions and the validation kernel, and
nothing else. The full design is docs/presentation.md.

Python validates the draft and lays it out as a PowerPoint deck — `pptx/`.
There was an HTML player before that, and the pivot to a file the teacher
can edit is docs/pptx.md.
"""

from physics_svg.presentation.manifest import (
    PresentationSpec,
    parse_presentation,
    parse_slide,
)
from physics_svg.presentation.slides import slide_annotation
from physics_svg.presentation.workspace import Workspace, WorkspaceError, load_workspace

__all__ = [
    "PresentationSpec",
    "Workspace",
    "WorkspaceError",
    "load_workspace",
    "parse_presentation",
    "parse_slide",
    "slide_annotation",
]
