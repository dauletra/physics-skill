"""Реестр компонентов уровня 2 — см. references/task-schema.md."""

from components.graph import GraphComponent
from components.list import ListComponent
from components.table import TableComponent
from components.text import TextComponent

COMPONENT_TYPES = {
    "text": TextComponent,
    "table": TableComponent,
    "graph": GraphComponent,
    "list": ListComponent,
}


def component_from_dict(data: dict):
    return COMPONENT_TYPES[data["type"]].from_dict(data)
