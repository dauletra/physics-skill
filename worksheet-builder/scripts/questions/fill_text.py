import re

from components.text import TextComponent
from questions.base import Question, envelope
from render_helpers import bank_list, esc

# Плейсхолдер `___имя___` — именованная ссылка на ключ `blanks` (единственный
# вид ссылки в этом payload: плейсхолдер и есть явный стабильный идентификатор).
BLANK_RE = re.compile(r"___(\w+)___")


class FillTextQuestion(Question):
    """Заполнить пропуск, носитель — текст."""

    type = "fill_text"

    def __init__(self, template, blanks=None, bank=None, **kwargs):
        super().__init__(**kwargs)
        self.template = template
        self.blanks = blanks or {}
        self.bank = bank

    def validate(self) -> None:
        placeholders = set(BLANK_RE.findall(self.template))
        if placeholders != set(self.blanks.keys()):
            raise ValueError(
                f"fill_text: template placeholders {placeholders} != blanks keys {set(self.blanks.keys())}"
            )

    def _resolve(self, is_teacher):
        pieces = []
        last = 0
        for m in BLANK_RE.finditer(self.template):
            pieces.append(esc(self.template[last : m.start()]))
            key = m.group(1)
            if is_teacher:
                pieces.append(f'<span class="fill-blank answered">{esc(self.blanks[key])}</span>')
            else:
                pieces.append('<span class="fill-blank"></span>')
            last = m.end()
        pieces.append(esc(self.template[last:]))
        return "".join(pieces)

    def render_body(self, mode, lang) -> str:
        body = TextComponent(body=self._resolve(mode == "teacher")).render()
        if self.bank:
            body = bank_list(lang, self.bank) + body
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "FillTextQuestion":
        return cls(
            template=data["template"],
            blanks=data.get("blanks", {}),
            bank=data.get("bank"),
            **envelope(data),
        )
