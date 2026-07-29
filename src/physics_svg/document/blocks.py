"""What may appear where — the block unions, assembled from the registries.

Nothing here is a list to maintain by hand. Components are the document's own
plus every registered illustration; questions are every registered question
type. A new illustration or a new pedagogical kind becomes usable inside a
task the moment its package exists.

The unions are `Deferred` because the registries are populated at import
time, after these containers are defined.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Union

from physics_svg.document.components import (
    AnswerLineSpec,
    HeadingSpec,
    ListSpec,
    TableSpec,
    TextSpec,
)
from physics_svg.document.questions import question_models
from physics_svg.schema import Deferred
from physics_svg.visuals import load_all as load_visuals

#: Document-only components — the illustrations join them from the registry.
TEXT_COMPONENTS = (TextSpec, TableSpec, ListSpec, AnswerLineSpec)


def component_models() -> tuple[type, ...]:
    return TEXT_COMPONENTS + tuple(entry.model for entry in load_visuals().values())


def component_annotation() -> Any:
    return Union[component_models()]


def question_annotation() -> Any:
    return Union[question_models()]


def task_block_annotation() -> Any:
    """Anything that can sit inside a task: components, questions, and the two
    containers."""
    from physics_svg.document.containers import PartSpec, RowSpec

    return Union[component_models() + question_models() + (PartSpec, RowSpec)]


def doc_block_annotation() -> Any:
    """One top-level block — the content of one `blocks/*.json` file."""
    from physics_svg.document.containers import DocRowSpec, TaskSpec

    return Union[(HeadingSpec, TaskSpec, DocRowSpec) + component_models()]


def doc_row_child_annotation() -> Any:
    """Children of a top-level row: components and headings only. Questions,
    parts and tasks in a top-level column are structurally inexpressible —
    which also rules out a nested row."""
    return Union[(HeadingSpec,) + component_models()]


if TYPE_CHECKING:  # mypy reads these as plain `Any`; at runtime they resolve
    TASK_BLOCK = Any
    DOC_BLOCK = Any
    DOC_ROW_CHILD = Any
else:
    TASK_BLOCK = Deferred(task_block_annotation)
    DOC_BLOCK = Deferred(doc_block_annotation)
    DOC_ROW_CHILD = Deferred(doc_row_child_annotation)
