from questions.base import Question
from render_helpers import answer_block, blank, lines
from strings import t


class OpenQuestion(Question):
    """Открытый вопрос (развёрнутый/короткий), "найти и исправить ошибку" —
    тот же класс, отличие только в содержимом `prompt`."""

    type = "open"

    def __init__(self, response="none", answer=None, **kwargs):
        super().__init__(**kwargs)
        self.response = response
        self.answer = answer

    def render(self, mode, lang) -> str:
        if self.response.startswith("lines:"):
            body = lines(int(self.response.split(":", 1)[1]))
        elif self.response == "blank":
            body = f'<div>{t(lang, "answer_label")} {blank()}</div>'
        else:
            body = ""
        if mode == "teacher" and self.answer:
            body += answer_block(lang, self.answer)
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "OpenQuestion":
        return cls(
            prompt=data.get("prompt", ""),
            label=data.get("label"),
            points=data.get("points"),
            response=data.get("response", "none"),
            answer=data.get("answer"),
        )
