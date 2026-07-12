import re

from components.table import TableComponent
from components.text import TextComponent
from questions.base import Question
from render_helpers import bank_list, blank_cell, esc

_BLANK_RE = re.compile(r"___(\w+)___")


class FillBlankTextQuestion(Question):
    """Заполнить пропуск, носитель — текст."""

    type = "fill_blank_text"

    def __init__(self, template, blanks=None, bank=None, **kwargs):
        super().__init__(**kwargs)
        self.template = template
        self.blanks = blanks or {}
        self.bank = bank

    def validate(self) -> None:
        placeholders = set(_BLANK_RE.findall(self.template))
        if placeholders != set(self.blanks.keys()):
            raise ValueError(
                f"fill_blank_text: template placeholders {placeholders} != blanks keys {set(self.blanks.keys())}"
            )

    def _resolve(self, is_teacher):
        pieces = []
        last = 0
        for m in _BLANK_RE.finditer(self.template):
            pieces.append(esc(self.template[last : m.start()]))
            key = m.group(1)
            if is_teacher:
                pieces.append(f'<span class="fill-blank answered">{esc(self.blanks[key])}</span>')
            else:
                pieces.append('<span class="fill-blank"></span>')
            last = m.end()
        pieces.append(esc(self.template[last:]))
        return "".join(pieces)

    def render(self, mode, lang) -> str:
        body = TextComponent(body=self._resolve(mode == "teacher")).render()
        if self.bank:
            body = bank_list(lang, self.bank) + body
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "FillBlankTextQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            template=data["template"],
            blanks=data.get("blanks", {}),
            bank=data.get("bank"),
        )


class FillBlankTableQuestion(Question):
    """Заполнить пропуск, носитель — таблица. `null` в `rows` — позиция
    пропуска (только на входе), `answers["r,c"]` — значение для учителя."""

    type = "fill_blank_table"

    def __init__(self, headers, rows, answers=None, bank=None, **kwargs):
        super().__init__(**kwargs)
        self.headers = headers
        self.rows = rows
        self.answers = answers or {}
        self.bank = bank

    def validate(self) -> None:
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row):
                if cell is None and f"{r},{c}" not in self.answers:
                    raise ValueError(f"fill_blank_table: blank at {r},{c} has no entry in answers")

    def render(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        resolved_rows = []
        for r, row in enumerate(self.rows):
            cells = []
            for c, cell in enumerate(row):
                if cell is None:
                    value = self.answers.get(f"{r},{c}")
                    cells.append(f'<span class="fill-blank answered">{esc(value)}</span>' if is_teacher and value is not None else blank_cell())
                else:
                    cells.append(esc(cell))
            resolved_rows.append(cells)
        body = TableComponent(headers=[esc(h) for h in self.headers], rows=resolved_rows).render()
        if self.bank:
            body = bank_list(lang, self.bank) + body
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "FillBlankTableQuestion":
        return cls(
            label=data.get("label"),
            points=data.get("points"),
            headers=data["headers"],
            rows=data["rows"],
            answers=data.get("answers", {}),
            bank=data.get("bank"),
        )
