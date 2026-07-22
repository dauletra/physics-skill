"""Рендер чистых компонентов (`text`/`table`/`graph`/`list`/`instrument`) —
только отрисовка, никакого знания об ответе/правильности/режиме
ученик-учитель.
Работают напрямую с pydantic-моделями (models.py) — параллельного слоя
данных нет.

Правило экранирования: модели хранят СЫРОЙ авторский текст, экранирует
рендер в точке интерполяции (`esc`). Хелперы `list_html`/`table_html`
принимают уже готовую HTML-безопасную разметку — ими пользуются и рендеры
компонентов (отдав туда экранированный текст), и функции вопросов
(questions.py), собирающие строки с галочками/квадратиками."""

from typing import Callable

from worksheet_builder.instruments import build_instrument_svg
from worksheet_builder.models import (
    AnswerLineModel,
    ComponentModel,
    GraphModel,
    InstrumentModel,
    ListModel,
    PaperModel,
    TableModel,
    TextModel,
)
from worksheet_builder.paper import build_paper_svg, paper_px_height
from worksheet_builder.render_helpers import blank, esc, fmt_num
from worksheet_builder.strings import LETTERS, t
from worksheet_builder.visuals import build_chart_svg


def list_html(items: list[str], marker: str = "none", columns: str = "single") -> str:
    """Разметка списка: последовательность пунктов с опциональной меткой
    сбоку (номер/буква). `items` — уже HTML-безопасные строки."""

    def marker_html(i: int) -> str:
        if marker == "number":
            return f'<span class="list-marker">{i + 1}.</span>'
        if marker == "letter":
            return f'<span class="list-marker">{LETTERS[i]})</span>'
        return ""

    rows = "".join(
        f'<div class="list-row">{marker_html(i)}<span class="list-content">{item}</span></div>'
        for i, item in enumerate(items)
    )
    return f'<div class="list-component cols-{columns}">{rows}</div>'


def table_html(headers: list[str], rows: list[list[str]]) -> str:
    """Разметка таблицы: настоящая двумерная сетка с подписанными колонками.
    `headers`/`rows` — уже HTML-безопасные строки."""
    thead = "".join(f"<th>{h}</th>" for h in headers)
    body_rows = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>" for row in rows
    )
    return (
        '<table class="table-component">'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{body_rows}</tbody>"
        "</table>"
    )


def render_text(model: TextModel) -> str:
    return f"<p>{esc(model.body)}</p>"


def render_table(model: TableModel) -> str:
    return table_html(
        [esc(h) for h in model.headers],
        [[esc(cell) for cell in row] for row in model.rows],
    )


def render_graph(model: GraphModel) -> str:
    return build_chart_svg(
        x_label=model.x_label,
        y_label=model.y_label,
        x_range=model.x_range,
        y_range=model.y_range,
        series=model.series,
        chart_type=model.chart_type,
    )


def render_list(model: ListModel) -> str:
    return list_html([esc(item) for item in model.items], model.marker, model.columns)


def render_instrument(model: InstrumentModel) -> str:
    return build_instrument_svg(model)


def render_paper(model: PaperModel) -> str:
    """Поле для работы ученика. Класс обёртки говорит CSS, откуда берётся
    ширина: `paper-fixed` — из данных (`cols`, квадратная клетка), тогда
    ширину несёт сам SVG; `paper-fluid` — вся колонка, и тогда обёртка
    отдаёт CSS заданную автором высоту (единственный размер, который в этом
    случае из данных, — см. paper.paper_px_height)."""
    if model.cols is not None:
        return f'<div class="paper-wrap paper-fixed">{build_paper_svg(model)}</div>'
    height = fmt_num(paper_px_height(model))
    return (
        f'<div class="paper-wrap paper-fluid" style="--paper-h:{height}px">'
        f"{build_paper_svg(model)}</div>"
    )


def render_answer_line(model: AnswerLineModel) -> str:
    return f'<div>{t("answer_label")} {blank()}</div>'


COMPONENT_RENDERERS: dict[type, Callable[..., str]] = {
    TextModel: render_text,
    TableModel: render_table,
    GraphModel: render_graph,
    ListModel: render_list,
    InstrumentModel: render_instrument,
    PaperModel: render_paper,
    AnswerLineModel: render_answer_line,
}


def render_component(model: ComponentModel) -> str:
    return COMPONENT_RENDERERS[type(model)](model)
