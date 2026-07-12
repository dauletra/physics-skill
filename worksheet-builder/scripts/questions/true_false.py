from components.list import ListComponent
from questions.base import Question
from render_helpers import esc
from strings import t


def _square(mark):
    return f'<span class="tf-square">{mark}</span>'


class TrueFalseQuestion(Question):
    """Да/нет. `correct` — индекс утверждения (строкой) → bool."""

    type = "true_false"

    def __init__(self, statements, correct=None, **kwargs):
        super().__init__(**kwargs)
        self.statements = statements
        self.correct = correct or {}

    def validate(self) -> None:
        for key, value in self.correct.items():
            if not (0 <= int(key) < len(self.statements)):
                raise ValueError(f"true_false: correct key {key!r} out of range for {len(self.statements)} statements")
            if not isinstance(value, bool):
                raise ValueError(f"true_false: correct[{key!r}] must be bool, got {value!r}")

    def render(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        items = []
        for i, statement in enumerate(self.statements):
            expected = self.correct.get(str(i))
            true_mark = "&#10005;" if is_teacher and expected is True else ""
            false_mark = "&#10005;" if is_teacher and expected is False else ""
            items.append(
                '<span class="tf-line">'
                f'<span class="tf-statement">{esc(statement)}</span>'
                '<span class="tf-box">'
                f'{_square(true_mark)} {t(lang, "true_label")}&nbsp;&nbsp;'
                f'{_square(false_mark)} {t(lang, "false_label")}'
                "</span>"
                "</span>"
            )
        return ListComponent(items=items, marker="none", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "TrueFalseQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            statements=data["statements"],
            correct=data.get("correct", {}),
        )
