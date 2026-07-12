from components.list import ListComponent
from questions.base import Question
from render_helpers import answer_block, esc, LOWER_LETTERS


class MatchingQuestion(Question):
    """Сопоставить. `right` — пул вариантов (может быть длиннее `left` —
    дистракторы). `pairs` — индекс в `left` (строкой, ключ JSON-объекта) →
    индекс в `right`."""

    type = "matching"

    def __init__(self, left, right, pairs, **kwargs):
        super().__init__(**kwargs)
        self.left = left
        self.right = right
        self.pairs = pairs

    def validate(self) -> None:
        for key, value in self.pairs.items():
            if not (0 <= int(key) < len(self.left)):
                raise ValueError(f"matching: pairs key {key!r} out of range for {len(self.left)} left items")
            if not (0 <= value < len(self.right)):
                raise ValueError(f"matching: pairs value {value!r} out of range for {len(self.right)} right items")

    def render(self, mode, lang) -> str:
        left_html = ListComponent(items=[esc(item) for item in self.left], marker="number").render()
        right_html = ListComponent(items=[esc(item) for item in self.right], marker="letter").render()
        body = f'<div class="matching-columns">{left_html}{right_html}</div>'
        if mode == "teacher":
            # Буквы в сводке соответствуют тем же строчным a)/b)/в), что и
            # реально напечатаны маркером ListComponent(marker="letter") у
            # правого списка — не заглавным, чтобы сводка не расходилась с
            # тем, что видит учитель на листе.
            summary = ", ".join(
                f"{i + 1}-{LOWER_LETTERS[self.pairs[str(i)]]}" for i in range(len(self.left))
            )
            body += answer_block(lang, summary)
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "MatchingQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            left=data["left"],
            right=data["right"],
            pairs=data["pairs"],
        )
