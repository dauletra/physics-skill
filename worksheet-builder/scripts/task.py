"""`Task` — корневой блок задания: дерево `blocks` из компонентов, вопросов и
контейнеров-`part` (см. references/task-schema.md). Буквы подзаданий и строки
заголовков вычисляются в document.py, не здесь — этот модуль отвечает только
за парсинг JSON в объекты и инварианты состава."""

from dataclasses import dataclass
from typing import Optional

from components import COMPONENT_TYPES, component_from_dict
from questions import QUESTION_TYPES, question_from_dict
from questions.base import Question


def _describe(data: dict, index: int) -> str:
    block_id = data.get("id") if isinstance(data, dict) else None
    return f"blocks[{index}]" + (f" (id={block_id})" if block_id else "")


def _leaf_from_dict(data: dict):
    block_type = data.get("type")
    if block_type in COMPONENT_TYPES:
        return component_from_dict(data)
    if block_type in QUESTION_TYPES:
        return question_from_dict(data)
    raise ValueError(f"unknown block type {block_type!r}")


def _validate_siblings(blocks, context: str):
    """Инвариант состава уровня списка: `part` и голый вопрос не бывают
    соседями; вопрос без `part` — не более одного (см. task-schema.md)."""
    parts = [b for b in blocks if isinstance(b, Part)]
    questions = [b for b in blocks if isinstance(b, Question)]
    if parts and questions:
        raise ValueError(f"{context}: 'part' and a bare question cannot be siblings - wrap every question in a part")
    if not parts and len(questions) > 1:
        raise ValueError(f"{context}: more than one bare question - wrap each question in its own 'part'")


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
            if raw.get("type") == "part":
                raise ValueError(f"{context} -> {_describe(raw, i)}: nested parts are not supported")
            try:
                blocks.append(_leaf_from_dict(raw))
            except ValueError as e:
                raise ValueError(f"{context} -> {_describe(raw, i)}: {e}") from None
        questions = [b for b in blocks if isinstance(b, Question)]
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
            if raw.get("type") == "part":
                blocks.append(Part.from_dict(raw, context))
            else:
                try:
                    blocks.append(_leaf_from_dict(raw))
                except ValueError as e:
                    raise ValueError(f"{context}: {e}") from None
        _validate_siblings(blocks, task_id)
        return cls(
            id=data["id"],
            blocks=blocks,
            points=data.get("points"),
        )
