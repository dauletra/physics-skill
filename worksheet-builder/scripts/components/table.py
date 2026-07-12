from components.base import Component
from render_helpers import esc


class TableComponent(Component):
    """Настоящая двумерная сетка с подписанными колонками. `rows` — всегда
    готовые строки (список списков строк) — заполнение пропусков для
    `fill_table` делает сам класс вопроса до вызова компонента, здесь
    нет знания о том, какая ячейка "пропуск", а какая — данность."""

    def __init__(self, headers: list, rows: list):
        self.headers = headers
        self.rows = rows

    def render(self) -> str:
        thead = "".join(f"<th>{h}</th>" for h in self.headers)
        body_rows = []
        for row in self.rows:
            cells = "".join(f"<td>{cell}</td>" for cell in row)
            body_rows.append(f"<tr>{cells}</tr>")
        return (
            '<table class="table-component">'
            f"<thead><tr>{thead}</tr></thead>"
            f"<tbody>{''.join(body_rows)}</tbody>"
            "</table>"
        )

    @classmethod
    def from_dict(cls, data: dict) -> "TableComponent":
        headers = [esc(h) for h in data.get("headers", [])]
        rows = [[esc(cell) for cell in row] for row in data.get("rows", [])]
        return cls(headers=headers, rows=rows)
