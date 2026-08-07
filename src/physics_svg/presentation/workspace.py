"""Loading a lesson's presentation draft: `presentation.json` plus one file
per slide.

The same two folder-level invariants as the document loader, for the same
reasons: a file in `slides/` that `order` does not list would be silently
dropped from the lesson — that is a build error, not "just not shown"; and a
slide whose `id` disagrees with its file name makes targeted editing a
guessing game. The loaders are deliberately parallel and deliberately
separate: the two genres share no code (docs/presentation.md §2), and each
folder speaks about its own files.

Every problem in the draft is collected and reported at once, so the author
fixes the whole folder in one pass instead of one error per run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from physics_svg.presentation.manifest import PresentationSpec, parse_presentation, parse_slide
from physics_svg.schema import SchemaError


class WorkspaceError(ValueError):
    """Problems found while loading a presentation draft, reported together."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass(frozen=True)
class Workspace:
    """A parsed presentation draft. Rendering works from the models; the raw
    JSON is kept for the same reason the document keeps it — what the author
    wrote must survive verbatim, not as a normalised round-trip."""

    presentation: PresentationSpec
    slides: list[Any]
    raw_presentation: Any
    raw_slides: list[Any]


def load_workspace(directory: str | Path) -> Workspace:
    folder = Path(directory)
    manifest_path = folder / "presentation.json"
    if not manifest_path.exists():
        raise WorkspaceError([f"не найден {manifest_path}"])

    raw_presentation = _read_json(manifest_path, folder)
    try:
        presentation = parse_presentation(raw_presentation)
    except SchemaError as error:
        raise WorkspaceError([str(error)]) from None

    slides_dir = folder / "slides"
    available = sorted(path.stem for path in slides_dir.glob("*.json"))
    order = presentation.order or available

    problems: list[str] = []
    unlisted = sorted(set(available) - set(order))
    if unlisted:
        problems.append(
            "presentation.json -> order: файлы слайдов есть, но не перечислены "
            f"(они молча выпали бы из урока): {', '.join(unlisted)}"
        )

    raw_slides: list[Any] = []
    models: list[Any] = []
    for slide_id in order:
        path = slides_dir / f"{slide_id}.json"
        if not path.exists():
            problems.append(f"не найден файл слайда: {path}")
            continue
        raw = _read_json(path, folder)
        raw_id = raw.get("id") if isinstance(raw, dict) else None
        if raw_id != slide_id:
            problems.append(
                f"{path.name}: id '{raw_id}' не совпадает с именем файла (ожидалось '{slide_id}')"
            )
        raw_slides.append(raw)
        try:
            models.append(parse_slide(raw, slide_id))
        except SchemaError as error:
            problems.append(str(error))

    if problems:
        raise WorkspaceError(problems)
    return Workspace(presentation, models, raw_presentation, raw_slides)


def _read_json(path: Path, root: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WorkspaceError([f"{path.relative_to(root)}: невалидный JSON — {error}"]) from None
