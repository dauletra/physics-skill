from components.base import Component
from render_helpers import esc


class TextComponent(Component):
    """Свободный текст. `body` поддерживает `<sup>`/`<sub>`/LaTeX как
    форматирование (см. references/symbols.md) — не педагогическое знание,
    просто разметка."""

    def __init__(self, body: str):
        self.body = body

    def render(self) -> str:
        return f"<p>{self.body}</p>"

    @classmethod
    def from_dict(cls, data: dict) -> "TextComponent":
        return cls(body=esc(data.get("body", "")))
