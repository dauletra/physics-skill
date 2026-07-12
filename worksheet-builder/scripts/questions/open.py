from questions.base import Question, envelope
from render_helpers import answer_block, blank, lines
from strings import t

_RESPONSES = ("blank", "none")


class OpenQuestion(Question):
    """Открытый вопрос (развёрнутый/короткий), "найти и исправить ошибку" —
    тот же класс, отличие только в соседнем `text`-блоке с условием."""

    type = "open"

    def __init__(self, response="none", answer=None, **kwargs):
        super().__init__(**kwargs)
        self.response = response
        self.answer = answer

    def validate(self) -> None:
        if self.response.startswith("lines:"):
            suffix = self.response.split(":", 1)[1]
            if not (suffix.isdigit() and int(suffix) > 0):
                raise ValueError(f"open: response 'lines:N' requires positive integer N, got {self.response!r}")
        elif self.response not in _RESPONSES:
            raise ValueError(f"open: response must be 'lines:N', 'blank' or 'none', got {self.response!r}")

    def render_body(self, mode, lang) -> str:
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
            response=data.get("response", "none"),
            answer=data.get("answer"),
            **envelope(data),
        )
