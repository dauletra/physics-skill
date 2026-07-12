"""`Task` — корневой блок задания: дерево `blocks` из компонентов, вопросов,
контейнеров-`part` и layout-контейнеров-`row` (см. references/task-schema.md).
Буквы подзаданий и строки заголовков вычисляются в document.py, не здесь —
этот модуль отвечает только за парсинг JSON в объекты и инварианты состава."""

from dataclasses import dataclass
from typing import Optional

from components import COMPONENT_TYPES, component_from_dict
from questions import QUESTION_TYPES, question_from_dict
from questions.base import Question


def _describe(data: dict, index: int) -> str:
    block_id = data.get("id") if isinstance(data, dict) else None
    return f"blocks[{index}]" + (f" (id={block_id})" if block_id else "")


def iter_flat(blocks):
    """Сплющенный обход списка блоков: `row` прозрачен — его дети считаются
    сиблингами на уровне родителя. Инварианты состава и раздача букв всегда
    работают по этому обходу: раскладка не может изменить смысл/нумерацию."""
    for block in blocks:
        if isinstance(block, Row):
            yield from block.blocks
        else:
            yield block


def _leaf_from_dict(data: dict):
    block_type = data.get("type")
    if block_type in COMPONENT_TYPES:
        return component_from_dict(data)
    if block_type in QUESTION_TYPES:
        return question_from_dict(data)
    raise ValueError(f"unknown block type {block_type!r}")


def _block_from_dict(data: dict, context: str, *, in_row: bool, allow_part: bool):
    if "width" in data:
        # Явное отклонение, а не молчаливое игнорирование: мёртвое поле в
        # данных — ловушка для автора (дети `row` всегда делят строку поровну).
        raise ValueError(f"{context}: 'width' is not supported - children of a 'row' share the line equally")
    block_type = data.get("type")
    if block_type == "row":
        if in_row:
            raise ValueError(f"{context}: nested rows are not supported")
        return Row.from_dict(data, context, allow_part=allow_part)
    if block_type == "part":
        if not allow_part:
            raise ValueError(f"{context}: nested parts are not supported")
        return Part.from_dict(data, context)
    try:
        return _leaf_from_dict(data)
    except ValueError as e:
        raise ValueError(f"{context}: {e}") from None


def _validate_siblings(blocks, context: str):
    """Инвариант состава уровня списка (по сплющенному обходу — `row`
    прозрачен): `part` и голый вопрос не бывают соседями; вопрос без `part`
    — не более одного (см. task-schema.md)."""
    flat = list(iter_flat(blocks))
    parts = [b for b in flat if isinstance(b, Part)]
    questions = [b for b in flat if isinstance(b, Question)]
    if parts and questions:
        raise ValueError(f"{context}: 'part' and a bare question cannot be siblings - wrap every question in a part")
    if not parts and len(questions) > 1:
        raise ValueError(f"{context}: more than one bare question - wrap each question in its own 'part'")


@dataclass
class Row:
    """Layout-контейнер: дочерние блоки стоят в одну строку и делят её
    поровну. Прозрачен для педагогических инвариантов и букв (см. iter_flat)
    — влияет только на геометрию."""

    blocks: list
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict, context: str, *, allow_part: bool) -> "Row":
        raw_blocks = data.get("blocks", [])
        if not raw_blocks:
            raise ValueError(f"{context}: row has no blocks")
        blocks = []
        for i, raw in enumerate(raw_blocks):
            child_context = f"{context} -> {_describe(raw, i)}"
            blocks.append(_block_from_dict(raw, child_context, in_row=True, allow_part=allow_part))
        return cls(blocks=blocks, id=data.get("id"))


@dataclass
class Part:
    """Контейнер подзадания: контекст (компоненты) + ровно один вопрос.
    Буква (`label`) — либо явная из JSON, либо проставляется в document.py."""

    blocks: list
    label: Optional[str] = None
    points: Optional[int] = None
    id: Optional[str] = None

    @classmethod
    def from_dict(cls, data: dict, context: str) -> "Part":
        raw_blocks = data.get("blocks", [])
        if not raw_blocks:
            raise ValueError(f"{context}: part has no blocks")
        blocks = []
        for i, raw in enumerate(raw_blocks):
            child_context = f"{context} -> {_describe(raw, i)}"
            blocks.append(_block_from_dict(raw, child_context, in_row=False, allow_part=False))
        questions = [b for b in iter_flat(blocks) if isinstance(b, Question)]
        if len(questions) != 1:
            raise ValueError(f"{context}: part must contain exactly one question, got {len(questions)}")
        return cls(
            blocks=blocks,
            label=data.get("label"),
            points=data.get("points"),
            id=data.get("id"),
        )


@dataclass
class Task:
    id: str
    blocks: list
    points: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        task_id = data.get("id", "<no id>")
        raw_blocks = data.get("blocks", [])
        if not raw_blocks:
            raise ValueError(f"Task {task_id} has no blocks")
        blocks = []
        for i, raw in enumerate(raw_blocks):
            context = f"{task_id} -> {_describe(raw, i)}"
            blocks.append(_block_from_dict(raw, context, in_row=False, allow_part=True))
        _validate_siblings(blocks, task_id)
        return cls(
            id=data["id"],
            blocks=blocks,
            points=data.get("points"),
        )
