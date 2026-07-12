from components.list import ListComponent
from questions.base import Question, envelope
from render_helpers import esc


class ChoiceQuestion(Question):
    """Выбор (один/много). `options` — список объектов `{text, correct?}`,
    правильность помечена инлайн на варианте."""

    type = "choice"

    def __init__(self, options, select="single", **kwargs):
        super().__init__(**kwargs)
        self.options = options
        self.select = select

    def validate(self) -> None:
        if not self.options:
            raise ValueError("choice: options must be non-empty")
        for i, option in enumerate(self.options):
            if not isinstance(option, dict) or "text" not in option:
                raise ValueError(f"choice: options[{i}] must be an object with 'text'")
        n_correct = sum(1 for o in self.options if o.get("correct"))
        if self.select == "single" and n_correct != 1:
            raise ValueError(f"choice: select='single' requires exactly one correct option, got {n_correct}")
        if self.select == "multiple" and n_correct == 0:
            raise ValueError("choice: select='multiple' requires at least one correct option")
        if self.select not in ("single", "multiple"):
            raise ValueError(f"choice: select must be 'single' or 'multiple', got {self.select!r}")

    def render_body(self, mode, lang) -> str:
        items = []
        for option in self.options:
            is_correct = mode == "teacher" and option.get("correct")
            mark = "&#10003;" if is_correct else ""
            css = "mc-correct" if is_correct else ""
            items.append(f'<span class="mc-marker">{mark}</span><span class="{css}">{esc(option["text"])}</span>')
        return ListComponent(items=items, marker="letter", columns="single").render()

    @classmethod
    def from_dict(cls, data: dict) -> "ChoiceQuestion":
        return cls(
            options=data["options"],
            select=data.get("select", "single"),
            **envelope(data),
        )
