from components.table import TableComponent
from questions.base import Question, envelope
from render_helpers import bank_list, blank_cell, esc


class FillTableQuestion(Question):
    """Заполнить пропуск, носитель — таблица. Форма `headers`/`rows` совпадает
    с компонентом `table`; ячейка-пропуск — объект `{"answer": "…"}` с ответом
    инлайн вместо готовой строки."""

    type = "fill_table"

    def __init__(self, headers, rows, bank=None, **kwargs):
        super().__init__(**kwargs)
        self.headers = headers
        self.rows = rows
        self.bank = bank

    def validate(self) -> None:
        has_blank = False
        for r, row in enumerate(self.rows):
            for c, cell in enumerate(row):
                if isinstance(cell, dict):
                    if not isinstance(cell.get("answer"), str):
                        raise ValueError(f"fill_table: blank cell at row {r}, col {c} must be {{'answer': str}}")
                    has_blank = True
                elif not isinstance(cell, str):
                    raise ValueError(f"fill_table: cell at row {r}, col {c} must be a string or {{'answer': str}}")
        if not has_blank:
            raise ValueError("fill_table: at least one cell must be a blank ({'answer': …})")

    def render_body(self, mode, lang) -> str:
        is_teacher = mode == "teacher"
        resolved_rows = []
        for row in self.rows:
            cells = []
            for cell in row:
                if isinstance(cell, dict):
                    cells.append(
                        f'<span class="fill-blank answered">{esc(cell["answer"])}</span>' if is_teacher else blank_cell()
                    )
                else:
                    cells.append(esc(cell))
            resolved_rows.append(cells)
        body = TableComponent(headers=[esc(h) for h in self.headers], rows=resolved_rows).render()
        if self.bank:
            body = bank_list(lang, self.bank) + body
        return body

    @classmethod
    def from_dict(cls, data: dict) -> "FillTableQuestion":
        return cls(
            headers=data["headers"],
            rows=data["rows"],
            bank=data.get("bank"),
            **envelope(data),
        )
