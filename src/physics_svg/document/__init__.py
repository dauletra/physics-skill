"""The document layer: blocks, questions, numbering, answers, HTML.

The artefact is a single **document** — a lesson summary, an explanation, a
set of exercises, or any combination: theory and tasks interleave freely and
task numbering skips the theory. There are no student/teacher modes. Task
bodies never contain answers; the answers are collected into a section at the
end, and the handout variant is that document without the section.

Illustrations are used through the visual registry, never reimplemented here.
"""

from physics_svg.document.blocks import (
    component_annotation,
    doc_block_annotation,
    question_annotation,
)
from physics_svg.document.containers import (
    DocRowSpec,
    PartSpec,
    RowSpec,
    TaskSpec,
    iter_flat,
    iter_flat_paths,
    part_labels,
    task_part_labels,
)
from physics_svg.document.manifest import (
    DocumentSpec,
    HeaderSpec,
    parse_block,
    parse_document,
)
from physics_svg.document.render import build_document, build_preview, render_source
from physics_svg.document.workspace import Workspace, WorkspaceError, load_workspace

__all__ = [
    "DocRowSpec",
    "DocumentSpec",
    "HeaderSpec",
    "PartSpec",
    "RowSpec",
    "TaskSpec",
    "Workspace",
    "WorkspaceError",
    "build_document",
    "build_preview",
    "component_annotation",
    "doc_block_annotation",
    "iter_flat",
    "iter_flat_paths",
    "load_workspace",
    "parse_block",
    "parse_document",
    "part_labels",
    "question_annotation",
    "render_source",
    "task_part_labels",
]
