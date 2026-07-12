from components.list import ListComponent
from questions.base import Question, envelope
from render_helpers import answer_block, esc, LOWER_LETTERS


class MatchQuestion(Question):
    """Сопоставить. `right` — пул вариантов с явными `id` (может быть длиннее
    `left` — дистракторы, на которые никто не ссылается); `left[].match` —
    ссылка на `right[].id`, поэтому перестановки списков ничего не ломают."""

    type = "match"

    def __init__(self, left, right, **kwargs):
        super().__init__(**kwargs)
        self.left = left
        self.right = right

    def validate(self) -> None:
        if not self.left or not self.right:
            raise ValueError("match: left and right must be non-empty")
        ids = [r.get("id") for r in self.right]
        if any(not i for i in ids):
            raise ValueError("match: every right item must have a non-empty 'id'")
        if len(set(ids)) != len(ids):
            raise ValueError(f"match: right ids must be unique, got {ids}")
        for i, item in enumerate(self.left):
            if item.get("match") not in set(ids):
                raise ValueError(f"match: left[{i}].match {item.get('match')!r} not found among right ids {ids}")

    def render_body(self, mode, lang) -> str:
        left_html = ListComponent(items=[esc(item["text"]) for item in self.left], marker="number").render()
        right_html = ListComponent(items=[esc(item["text"]) for item in self.right], marker="letter").render()
        body = f'<div class="match-columns">{left_html}{right_html}</div>'
        if mode == "teacher":
            # Буквы в сводке — те же строчные a)/b), что реально напечатаны
            # маркером ListComponent(marker="letter") у правого списка:
            # печатная буква позиционная, связь — по id.
            id_to_letter = {item["id"]: LOWER_LETTERS[j] for j, item in enumerate(self.right)}
            summary = ", ".join(
                f"{i + 1}-{id_to_letter[item['match']]}" for i, item in enumerate(self.left)
            )
            body += answer_block(lang, summary)
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "MatchQuestion":
        return cls(
            left=data["left"],
            right=data["right"],
            **envelope(data),
        )
