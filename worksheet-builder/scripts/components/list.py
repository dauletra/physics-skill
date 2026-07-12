from components.base import Component
from render_helpers import esc, LOWER_LETTERS


class ListComponent(Component):
    """Последовательность пунктов с опциональной меткой сбоку (галочка,
    квадратик, номер, буква) — не двумерная сетка (см. "Почему list, а не
    всегда table" в references/task-schema.md). `items` — уже готовые строки:
    класс вопроса сам вставил в них любую сырую разметку (галочки/квадратики)
    через свои приватные хелперы, `ListComponent` их не эскейпит повторно."""

    def __init__(self, items: list, marker: str = "none", columns: str = "single"):
        self.items = items
        self.marker = marker
        self.columns = columns

    def _marker_html(self, i: int) -> str:
        if self.marker == "number":
            return f'<span class="list-marker">{i + 1}.</span>'
        if self.marker == "letter":
            return f'<span class="list-marker">{LOWER_LETTERS[i]})</span>'
        return ""

    def render(self) -> str:
        rows = "".join(
            f'<div class="list-row">{self._marker_html(i)}<span class="list-content">{item}</span></div>'
            for i, item in enumerate(self.items)
        )
        return f'<div class="list-component cols-{self.columns}">{rows}</div>'

    @classmethod
    def from_dict(cls, data: dict) -> "ListComponent":
        return cls(
            items=[esc(item) for item in data.get("items", [])],
            marker=data.get("marker", "none"),
            columns=data.get("columns", "single"),
        )
