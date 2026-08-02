"""Containers: subtask, row, task, and the top-level row.

Two of the project's structural rules live here.

**Meaning is expressed by nesting, never by adjacency.** "This text belongs
to this question", "these blocks are one subtask" — if a relation matters,
there is a container for it. Being next to something means nothing except
order on the page.

**Every container declares whether it is transparent.** `part` is a
pedagogical unit and is opaque; `row` is layout and is transparent — for
composition rules and for lettering it is walked through as though it were
not there. Layout can change geometry and nothing else.
"""

from __future__ import annotations

from typing import Iterator, Literal, Optional

from physics_svg.document.blocks import DOC_ROW_CHILD, TASK_BLOCK
from physics_svg.document.components import TextSpec
from physics_svg.document.questions import is_question
from physics_svg.document.strings import LETTERS
from physics_svg.schema import Invalid, field, spec

#: More than four columns on an A4 page leaves nothing but hyphenation.
MAX_COLUMNS = 4

#: The doc is shared: `row` means the same thing at both levels, so the field
#: it is documented by has to read identically in both tables.
COLUMNS_DOC = (
    "Сколько колонок; по умолчанию — по одной на каждого ребёнка. "
    "Дети заполняют колонки сверху вниз: при восьми детях и двух колонках "
    "первые четыре встанут слева, остальные справа"
)


def check_columns(columns: Optional[int], blocks: list) -> None:
    """Explicit columns are a wrapping instruction, not a table width.

    Asking for more columns than there are children would print empty ones,
    which reads as a rendering bug rather than as the author's intent.
    """
    if columns is not None and columns > len(blocks):
        raise Invalid(
            f"колонок {columns}, а детей {len(blocks)} — лишние останутся пустыми",
            field="columns",
        )


@spec
class RowSpec:
    """Layout-контейнер: дети делят строку поровну; с `columns` — переносятся
    по колонкам."""

    type: Literal["row"]
    blocks: list[TASK_BLOCK] = field(min_items=1)
    id: Optional[str] = None
    columns: Optional[int] = field(default=None, ge=2, le=MAX_COLUMNS, doc=COLUMNS_DOC)

    def check(self) -> None:
        if any(isinstance(block, RowSpec) for block in self.blocks):
            raise Invalid("строку нельзя вложить в строку", field="blocks")
        check_columns(self.columns, self.blocks)


@spec
class PartSpec:
    """Подзадание а)/б)/в) — компоненты плюс ровно один вопрос."""

    type: Literal["part"]
    blocks: list[TASK_BLOCK] = field(min_items=1)
    id: Optional[str] = None
    label: Optional[str] = field(default=None, doc="Явная буква; иначе выдаётся по порядку")

    def check(self) -> None:
        if self.label is not None and not (len(self.label) == 1 and self.label in LETTERS):
            # An explicit label lives in the same enumeration as the automatic
            # ones, or a sheet would carry two systems of numbering at once.
            raise Invalid(
                f"буква подзадания должна быть одной из '{LETTERS}', получено '{self.label}'",
                field="label",
            )
        flat = list(iter_flat(self.blocks))
        if any(isinstance(block, PartSpec) for block in flat):
            raise Invalid("подзадание нельзя вложить в подзадание", field="blocks")
        questions = [block for block in flat if is_question(block)]
        if len(questions) != 1:
            raise Invalid(
                f"в подзадании должен быть ровно один вопрос, получено {len(questions)}",
                field="blocks",
            )


@spec
class TaskSpec:
    """Нумерованное задание — единственный носитель вопросов в документе.

    Номер не хранится: он присваивается при сборке по порядку появления
    заданий, и теория между ними нумерацию не сдвигает.
    """

    type: Literal["task"]
    blocks: list[TASK_BLOCK] = field(min_items=1)
    id: Optional[str] = None

    def check(self) -> None:
        flat = list(iter_flat(self.blocks))
        parts = [block for block in flat if isinstance(block, PartSpec)]
        questions = [block for block in flat if is_question(block)]
        if parts and questions:
            raise Invalid(
                "подзадание и голый вопрос не бывают соседями — заверни каждый вопрос в 'part'",
                field="blocks",
            )
        if not parts and len(questions) > 1:
            raise Invalid(
                "больше одного вопроса без подзаданий — заверни каждый в свой 'part'",
                field="blocks",
            )
        if len(parts) > len(LETTERS):
            raise Invalid(
                f"не больше {len(LETTERS)} подзаданий в задании (буквенные метки), "
                f"получено {len(parts)}",
                field="blocks",
            )
        labels = [part.label for part in parts if part.label]
        duplicated = sorted({label for label in labels if labels.count(label) > 1})
        if duplicated:
            raise Invalid(f"явные буквы подзаданий повторяются: {duplicated}", field="blocks")
        self._check_unique_ids()
        self._check_condition()

    def _check_condition(self) -> None:
        """A question always has a statement beside it.

        Without one a task prints apparatus with no wording — options,
        statements, axes — and an `open` question prints nothing but its
        number, while a line still appears in the answers section and the
        document contradicts itself.

        The requirement is along the path to the root, not on every node: a
        `text` at task level covers all its subtasks, so a shared statement
        ("Determine the readings") need not be repeated. Only `text` counts —
        a narrow rule an author can remember; a graph caption or list items
        are not promoted to the role.
        """
        if any(isinstance(block, TextSpec) for block in iter_flat(self.blocks)):
            return
        for path, block in iter_flat_paths(self.blocks):
            if is_question(block):
                raise Invalid(
                    f"{path}: у вопроса нет условия — добавь блок 'text' с формулировкой",
                    field="blocks",
                )
            if isinstance(block, PartSpec) and not any(
                isinstance(inner, TextSpec) for inner in iter_flat(block.blocks)
            ):
                raise Invalid(
                    f"{path}: у подзадания нет условия — добавь блок 'text' сюда "
                    "или на уровень задания",
                    field="blocks",
                )

    def _check_unique_ids(self) -> None:
        seen: dict[str, str] = {}

        def walk(blocks: list, path: str) -> None:
            for i, block in enumerate(blocks):
                here = f"{path}[{i}]"
                block_id = getattr(block, "id", None)
                if block_id:
                    if block_id in seen:
                        raise Invalid(
                            f"id '{block_id}' повторяется: {here} и {seen[block_id]}",
                            field="blocks",
                        )
                    seen[block_id] = here
                if isinstance(block, (PartSpec, RowSpec)):
                    walk(block.blocks, f"{here}.blocks")

        walk(self.blocks, "blocks")


@spec
class DocRowSpec:
    """Верхнеуровневая строка документа: те же колонки, но дети — только
    компоненты и подзаголовки."""

    type: Literal["row"]
    blocks: list[DOC_ROW_CHILD] = field(min_items=1)
    id: Optional[str] = None
    columns: Optional[int] = field(default=None, ge=2, le=MAX_COLUMNS, doc=COLUMNS_DOC)

    def check(self) -> None:
        check_columns(self.columns, self.blocks)


# --- walking the tree ---------------------------------------------------


def iter_flat_paths(blocks: list) -> Iterator[tuple[str, object]]:
    """Flattened walk with the path to each block.

    `row` is transparent: its children count as siblings one level up, but
    keep their real position in the path (`blocks[1].blocks[0]`) so the
    author can find the block in the file. The transparency rule exists here
    in exactly one copy.
    """
    for i, block in enumerate(blocks):
        if isinstance(block, RowSpec):
            for j, inner in enumerate(block.blocks):
                yield f"blocks[{i}].blocks[{j}]", inner
        else:
            yield f"blocks[{i}]", block


def iter_flat(blocks: list) -> Iterator[object]:
    """The same walk without paths. Composition rules and subtask lettering
    both run on it, so layout cannot change meaning or numbering."""
    for _path, block in iter_flat_paths(blocks):
        yield block


def part_labels(parts: list[PartSpec]) -> dict[int, str]:
    """Letter per subtask, in order of appearance.

    An explicit `label` wins; automatic letters skip anything an explicit one
    has taken. Pure function — the same task letters the same way however
    many times it is rendered.
    """
    explicit = {part.label for part in parts if part.label}
    automatic = iter(letter for letter in LETTERS if letter not in explicit)
    return {id(part): part.label or next(automatic) for part in parts}


def task_part_labels(task: TaskSpec) -> dict[int, str]:
    # Letters follow the flattened walk: a part inside a row is lettered
    # exactly as it would be standing at task level.
    return part_labels([b for b in iter_flat(task.blocks) if isinstance(b, PartSpec)])
