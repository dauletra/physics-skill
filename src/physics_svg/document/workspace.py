"""Loading a draft folder: `document.json` plus one file per block.

Two invariants belong here rather than in a spec, because they are about the
folder and not about any one file:

* a file in `blocks/` that `order` does not list would be silently dropped
  from the document — that is a build error, not "just not shown";
* a block whose `id` disagrees with its file name makes targeted editing a
  guessing game.

Every problem in the draft is collected and reported at once, so the author
fixes the whole folder in one pass instead of one error per run.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from physics_svg.document.manifest import DocumentSpec, parse_block, parse_document
from physics_svg.schema import SchemaError


class WorkspaceError(ValueError):
    """Problems found while loading a draft folder, reported together."""

    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass(frozen=True)
class Workspace:
    """A parsed draft.

    `raw_document` and `raw_blocks` are the author's JSON exactly as written;
    their only consumer is the draft embedded in the finished HTML, which must
    carry what the author wrote rather than a normalised round-trip. Rendering
    works from the models.
    """

    document: DocumentSpec
    blocks: list[Any]
    raw_document: Any
    raw_blocks: list[Any]

    @property
    def source(self) -> dict[str, Any]:
        return {"document": self.raw_document, "blocks": self.raw_blocks}


def load_workspace(directory: str | Path) -> Workspace:
    folder = Path(directory)
    manifest_path = folder / "document.json"
    if not manifest_path.exists():
        raise WorkspaceError([f"не найден {manifest_path}"])

    raw_document = _read_json(manifest_path, folder)
    try:
        document = parse_document(raw_document)
    except SchemaError as error:
        raise WorkspaceError([str(error)]) from None

    blocks_dir = folder / "blocks"
    available = sorted(path.stem for path in blocks_dir.glob("*.json"))
    order = document.order or available

    problems: list[str] = []
    unlisted = sorted(set(available) - set(order))
    if unlisted:
        problems.append(
            "document.json -> order: файлы блоков есть, но не перечислены "
            f"(они молча выпали бы из документа): {', '.join(unlisted)}"
        )

    raw_blocks: list[Any] = []
    models: list[Any] = []
    for block_id in order:
        path = blocks_dir / f"{block_id}.json"
        if not path.exists():
            problems.append(f"не найден файл блока: {path}")
            continue
        raw = _read_json(path, folder)
        raw_id = raw.get("id") if isinstance(raw, dict) else None
        if raw_id != block_id:
            problems.append(
                f"{path.name}: id '{raw_id}' не совпадает с именем файла (ожидалось '{block_id}')"
            )
        raw_blocks.append(raw)
        try:
            models.append(parse_block(raw, block_id))
        except SchemaError as error:
            problems.append(str(error))

    if problems:
        raise WorkspaceError(problems)
    return Workspace(document, models, raw_document, raw_blocks)


def _read_json(path: Path, root: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise WorkspaceError([f"{path.relative_to(root)}: невалидный JSON — {error}"]) from None
