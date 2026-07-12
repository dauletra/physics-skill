from components.list import ListComponent
from questions.base import Question
from render_helpers import answer_block, esc


class ChoiceQuestion(Question):
    """Выбор (один/много)."""

    type = "choice"

    def __init__(self, options, correct=None, select_mode="single", explanation=None, **kwargs):
        super().__init__(**kwargs)
        self.options = options
        self.correct = correct or []
        self.select_mode = select_mode
        self.explanation = explanation

    def validate(self) -> None:
        n = len(self.options)
        for i in self.correct:
            if not (0 <= i < n):
                raise ValueError(f"choice: correct index {i} out of range for {n} options")
        if self.select_mode == "single" and len(self.correct) != 1:
            raise ValueError(
                f"choice: select_mode='single' requires exactly one correct index, got {self.correct}"
            )

    def render(self, mode, lang) -> str:
        correct_set = set(self.correct)
        items = []
        for i, option in enumerate(self.options):
            is_correct = mode == "teacher" and i in correct_set
            mark = "&#10003;" if is_correct else ""
            css = "mc-correct" if is_correct else ""
            items.append(f'<span class="mc-marker">{mark}</span><span class="{css}">{esc(option)}</span>')
        body = ListComponent(items=items, marker="letter", columns="single").render()
        if mode == "teacher" and self.explanation:
            body += answer_block(lang, self.explanation)
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "ChoiceQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            options=data["options"],
            correct=data.get("correct", []),
            select_mode=data.get("select_mode", "single"),
            explanation=data.get("explanation"),
        )
