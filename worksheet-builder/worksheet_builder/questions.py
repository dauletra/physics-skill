"""Рендер вопросов — по одной функции на педагогический вид. Функция
получает pydantic-модель вопроса (models.py; контент и ответ инлайн — см.
references/task-schema.md) и режим, и сама решает, что показать ученику,
а что учителю. Дерево приходит уже валидным — инварианты здесь не
перепроверяются.

Конверт одинаков у всех видов: `type` + опциональные `id`/`explanation` —
общая обработка (`explanation`-рамка в тичер-режиме) живёт в
`render_question`, видовые функции рендерят только тело. Нумерация и баллы
на вопросе не живут — это метаданные контейнеров (document.py).

Правило экранирования — как у компонентов (components.py): модель хранит
сырой текст, `esc()` вызывается в точке интерполяции; в `list_html`/
`table_html` передаётся уже готовая безопасная разметка."""

from typing import Callable, Literal

from worksheet_builder.components import list_html, table_html
from worksheet_builder.models import (
    BLANK_RE,
    ChoiceModel,
    ClassifyModel,
    FillTableModel,
    FillTextModel,
    MatchModel,
    OpenModel,
    PlotModel,
    QuestionModel,
    RankModel,
    TrueFalseModel,
)
from worksheet_builder.render_helpers import (
    answer_block,
    bank_list,
    blank,
    blank_cell,
    esc,
    lines,
)
from worksheet_builder.strings import LETTERS, t
from worksheet_builder.visuals import build_chart_svg

RenderMode = Literal["student", "teacher"]


def render_open(q: OpenModel, mode: RenderMode) -> str:
    """Открытый вопрос (развёрнутый/короткий); "найти и исправить ошибку" —
    тот же вид, отличие только в соседнем `text`-блоке с условием."""
    if q.response.startswith("lines:"):
        body = lines(int(q.response.split(":", 1)[1]))
    elif q.response == "blank":
        body = f'<div>{t("answer_label")} {blank()}</div>'
    else:
        body = ""
    if mode == "teacher" and q.answer:
        body += answer_block(q.answer)
    return body


def render_choice(q: ChoiceModel, mode: RenderMode) -> str:
    """Выбор (один/много); правильность помечена инлайн на варианте."""
    items = []
    for option in q.options:
        is_correct = mode == "teacher" and option.correct
        mark = "&#10003;" if is_correct else ""
        css = "mc-correct" if is_correct else ""
        items.append(
            f'<span class="mc-marker">{mark}</span><span class="{css}">{esc(option.text)}</span>'
        )
    body = list_html(items, marker="letter")
    if q.select == "multiple":
        # Иначе ученику неоткуда узнать, что верных ответов больше одного:
        # single и multiple рендерятся одинаковым списком.
        body = f'<div class="choice-hint">{t("choice_multiple_hint")}</div>' + body
    return body


def render_match(q: MatchModel, mode: RenderMode) -> str:
    """Сопоставить. `right` — пул вариантов с явными `id` (дистракторы
    допустимы); `left[].match` — ссылка на `right[].id`, поэтому перестановки
    списков ничего не ломают."""
    left_html = list_html([esc(item.text) for item in q.left], marker="number")
    right_html = list_html([esc(item.text) for item in q.right], marker="letter")
    body = f'<div class="match-columns">{left_html}{right_html}</div>'
    if mode == "teacher":
        # Буквы в сводке — те же а)/б), что реально напечатаны маркером
        # правого списка: печатная буква позиционная, связь — по id,
        # источник букв один (strings.LETTERS).
        id_to_letter = {item.id: LETTERS[j] for j, item in enumerate(q.right)}
        summary = ", ".join(
            f"{i + 1}-{id_to_letter[item.match]}" for i, item in enumerate(q.left)
        )
        body += answer_block(summary)
    return body


def render_fill_text(q: FillTextModel, mode: RenderMode) -> str:
    """Заполнить пропуск, носитель — текст. Плейсхолдер `___имя___` — ключ
    `blanks` (регэксп общий с валидацией — BLANK_RE в models.py)."""
    is_teacher = mode == "teacher"
    pieces = []
    last = 0
    for m in BLANK_RE.finditer(q.template):
        pieces.append(esc(q.template[last : m.start()]))
        if is_teacher:
            pieces.append(f'<span class="fill-blank answered">{esc(q.blanks[m.group(1)])}</span>')
        else:
            pieces.append('<span class="fill-blank"></span>')
        last = m.end()
    pieces.append(esc(q.template[last:]))
    body = f'<p>{"".join(pieces)}</p>'
    if q.bank:
        body = bank_list(q.bank) + body
    return body


def render_fill_table(q: FillTableModel, mode: RenderMode) -> str:
    """Заполнить пропуск, носитель — таблица. Форма `headers`/`rows` совпадает
    с компонентом `table`; ячейка-пропуск — `{"answer": …}` с ответом инлайн."""
    is_teacher = mode == "teacher"
    resolved_rows = []
    for row in q.rows:
        cells = []
        for cell in row:
            if isinstance(cell, str):
                cells.append(esc(cell))
            elif is_teacher:
                cells.append(f'<span class="fill-blank answered">{esc(cell.answer)}</span>')
            else:
                cells.append(blank_cell())
        resolved_rows.append(cells)
    body = table_html([esc(h) for h in q.headers], resolved_rows)
    if q.bank:
        body = bank_list(q.bank) + body
    return body


def render_plot(q: PlotModel, mode: RenderMode) -> str:
    """Построить график. `given` — серии, уже данные ученику на осях;
    `answer` — серии правильного ответа, рисуются только у учителя."""
    series = q.answer if mode == "teacher" else (q.given or [])
    return build_chart_svg(
        x_label=q.x_label,
        y_label=q.y_label,
        x_range=q.x_range,
        y_range=q.y_range,
        series=series,
        chart_type=q.chart_type,
    )


def _square(mark: str) -> str:
    return f'<span class="tf-square">{mark}</span>'


def render_true_false(q: TrueFalseModel, mode: RenderMode) -> str:
    """Да/нет; правильный ответ помечен инлайн на каждом утверждении."""
    is_teacher = mode == "teacher"
    items = []
    for statement in q.statements:
        true_mark = "&#10005;" if is_teacher and statement.answer is True else ""
        false_mark = "&#10005;" if is_teacher and statement.answer is False else ""
        items.append(
            '<span class="tf-line">'
            f'<span class="tf-statement">{esc(statement.text)}</span>'
            '<span class="tf-box">'
            f'{_square(true_mark)} {t("true_label")}&nbsp;&nbsp;'
            f'{_square(false_mark)} {t("false_label")}'
            "</span>"
            "</span>"
        )
    return list_html(items)


def render_rank(q: RankModel, mode: RenderMode) -> str:
    """Упорядочивание. Порядок массива — порядок показа (перемешанный);
    `position` — правильная позиция инлайн у каждого пункта."""
    is_teacher = mode == "teacher"
    items = []
    for item in q.items:
        position = item.position if is_teacher else ""
        items.append(
            '<span class="tf-line">'
            f'<span class="tf-statement">{esc(item.text)}</span>'
            f'<span class="rank-square">{position}</span>'
            "</span>"
        )
    return list_html(items)


def render_classify(q: ClassifyModel, mode: RenderMode) -> str:
    """Классифицировать. `category` — инлайн у каждого объекта; категория
    без объектов допустима (дистрактор)."""
    if mode == "teacher":
        items_html = list_html([esc(item.text) for item in q.items])
        # Сводка по категориям в авторском порядке `categories`; пустая
        # категория показывается прочерком. Строка — сырой текст:
        # экранирует answer_block, один раз.
        groups = []
        for category in q.categories:
            texts = [item.text for item in q.items if item.category == category]
            groups.append(f"{category}: {', '.join(texts) if texts else '—'}")
        return items_html + answer_block("; ".join(groups))
    rows = [
        f'<span class="tf-line"><span class="tf-statement">{esc(item.text)}</span>{blank(115)}</span>'
        for item in q.items
    ]
    return list_html(rows)


QUESTION_RENDERERS: dict[type, Callable[..., str]] = {
    OpenModel: render_open,
    ChoiceModel: render_choice,
    MatchModel: render_match,
    FillTextModel: render_fill_text,
    FillTableModel: render_fill_table,
    PlotModel: render_plot,
    TrueFalseModel: render_true_false,
    RankModel: render_rank,
    ClassifyModel: render_classify,
}


def render_question(q: QuestionModel, mode: RenderMode) -> str:
    """Тело вопроса + (в тичер-режиме) `explanation` — единообразно для всех
    видов. Пояснение печатается под своей подписью ("Пояснение:"), не под
    "Ответ:" — у видов с собственным ответом обе рамки различимы."""
    body = QUESTION_RENDERERS[type(q)](q, mode)
    if mode == "teacher" and q.explanation:
        body += answer_block(q.explanation, label_key="explanation_label")
    return body
