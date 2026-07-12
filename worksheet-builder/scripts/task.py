"""`Task` — единый разнородный список `items` (Component | Question), см.
references/task-schema.md. Буквы/строка заголовка вычисляются в document.py,
не здесь — этот модуль отвечает только за парсинг JSON в объекты."""

from dataclasses import dataclass, field

from components import COMPONENT_TYPES, component_from_dict
from questions import QUESTION_TYPES, question_from_dict


def item_from_dict(data: dict):
    item_type = data["type"]
    if item_type in COMPONENT_TYPES:
        return component_from_dict(data)
    if item_type in QUESTION_TYPES:
        return question_from_dict(data)
    raise ValueError(f"Unknown item type {item_type!r}")


@dataclass
class Task:
    id: str
    items: list
    points: int = None
    layout: list = None
    settings: dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        items = [item_from_dict(d) for d in data.get("items", [])]
        if not items:
            raise ValueError(f"Task {data.get('id')} has no items")
        return cls(
            id=data["id"],
            items=items,
            points=data.get("points"),
            layout=data.get("layout"),
            settings=data.get("settings", {}),
        )
