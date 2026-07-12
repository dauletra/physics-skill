from components.list import ListComponent
from questions.base import Question
from render_helpers import esc


class RankingQuestion(Question):
    """Упорядочивание. `items` — в перемешанном порядке показа;
    `correct_order` — верная позиция (1..N, перестановка без повторов),
    индекс `items` строкой → позиция."""

    type = "ranking"

    def __init__(self, items, correct_order=None, **kwargs):
        super().__init__(**kwargs)
        self.items = items
        self.correct_order = correct_order or {}

    def validate(self) -> None:
        n = len(self.items)
        keys = {int(k) for k in self.correct_order.keys()}
        if keys != set(range(n)):
            raise ValueError(f"ranking: correct_order keys must cover 0..{n - 1}, got {sorted(keys)}")
        positions = sorted(self.correct_order.values())
        if positions != list(range(1, n + 1)):
            raise ValueError(f"ranking: correct_order values must be a permutation of 1..{n}, got {positions}")

    def render(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        rows = []
        for i, item in enumerate(self.items):
            position = self.correct_order.get(str(i), "") if is_teacher else ""
            rows.append(
                '<span class="tf-line">'
                f'<span class="tf-statement">{esc(item)}</span>'
                f'<span class="rank-square">{position}</span>'
                "</span>"
            )
        return ListComponent(items=rows, marker="none", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "RankingQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            items=data["items"],
            correct_order=data.get("correct_order", {}),
        )
