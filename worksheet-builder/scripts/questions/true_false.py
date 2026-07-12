from components.list import ListComponent
from questions.base import Question, envelope
from render_helpers import esc
from strings import t


def _square(mark):
    return f'<span class="tf-square">{mark}</span>'


class TrueFalseQuestion(Question):
    """Да/нет. `statements` — список объектов `{text, answer}`, правильный
    ответ помечен инлайн на каждом утверждении."""

    type = "true_false"

    def __init__(self, statements, **kwargs):
        super().__init__(**kwargs)
        self.statements = statements

    def validate(self) -> None:
        if not self.statements:
            raise ValueError("true_false: statements must be non-empty")
        for i, statement in enumerate(self.statements):
            if not isinstance(statement, dict) or "text" not in statement:
                raise ValueError(f"true_false: statements[{i}] must be an object with 'text'")
            if not isinstance(statement.get("answer"), bool):
                raise ValueError(f"true_false: statements[{i}].answer must be bool, got {statement.get('answer')!r}")

    def render_body(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        items = []
        for statement in self.statements:
            expected = statement["answer"]
            true_mark = "&#10005;" if is_teacher and expected is True else ""
            false_mark = "&#10005;" if is_teacher and expected is False else ""
            items.append(
                '<span class="tf-line">'
                f'<span class="tf-statement">{esc(statement["text"])}</span>'
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
            statements=data["statements"],
            **envelope(data),
        )
