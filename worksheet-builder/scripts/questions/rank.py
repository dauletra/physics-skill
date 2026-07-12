from components.list import ListComponent
from questions.base import Question, envelope
from render_helpers import esc


class RankQuestion(Question):
    """Упорядочивание. Порядок массива `items` — порядок показа
    (перемешанный); `position` — правильная позиция `1..N` инлайн у каждого
    пункта."""

    type = "rank"

    def __init__(self, items, **kwargs):
        super().__init__(**kwargs)
        self.items = items

    def validate(self) -> None:
        if not self.items:
            raise ValueError("rank: items must be non-empty")
        for i, item in enumerate(self.items):
            if not isinstance(item, dict) or "text" not in item:
                raise ValueError(f"rank: items[{i}] must be an object with 'text'")
        n = len(self.items)
        positions = sorted(item.get("position") for item in self.items)
        if positions != list(range(1, n + 1)):
            raise ValueError(f"rank: positions must be a permutation of 1..{n}, got {positions}")

    def render_body(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        rows = []
        for item in self.items:
            position = item["position"] if is_teacher else ""
            rows.append(
                '<span class="tf-line">'
                f'<span class="tf-statement">{esc(item["text"])}</span>'
                f'<span class="rank-square">{position}</span>'
                "</span>"
            )
        return ListComponent(items=rows, marker="none", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "RankQuestion":
        return cls(
            items=data["items"],
            **envelope(data),
        )
