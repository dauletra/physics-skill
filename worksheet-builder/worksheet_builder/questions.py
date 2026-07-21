"""Рендер вопросов — по паре функций на педагогический вид: тело (то, что
видит решающий: пустые бланки, немаркированные варианты) и компактный ответ
для секции «Ответы» в конце документа. Функции получают pydantic-модель
вопроса (models.py; контент и ответ инлайн — см.
references/document-schema.md). Дерево приходит уже валидным — инварианты
здесь не перепроверяются.

Конверт одинаков у всех видов: `type` + опциональные `id`/`explanation`.
`explanation` телом не рендерится — его печатает сборщик секции ответов
(document.py) один раз для всех видов. Нумерация и баллы на вопросе не
живут — это метаданные контейнеров (document.py).

Правило экранирования — как у компонентов (components.py): модель хранит
сырой текст, `esc()` вызывается в точке интерполяции; в `list_html`/
`table_html` передаётся уже готовая безопасная разметка."""

from typing import Callable

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
    bank_list,
    blank,
    blank_cell,
    esc,
    lines,
)
from worksheet_builder.strings import LETTERS, t
from worksheet_builder.visuals import build_chart_svg

# --- Тела вопросов (то, что печатается в документе на месте задания) ---

def render_open(q: OpenModel) -> str:
    """Открытый вопрос (развёрнутый/короткий); "найти и исправить ошибку" —
    тот же вид, отличие только в соседнем `text`-блоке с условием."""
    if q.response.startswith("lines:"):
        return lines(int(q.response.split(":", 1)[1]))
    if q.response == "blank":
        return f'<div>{t("answer_label")} {blank()}</div>'
    return ""


def render_choice(q: ChoiceModel) -> str:
    """Выбор (один/много); правильность в теле никак не помечена — она
    печатается буквой в секции ответов."""
    body = list_html([esc(option.text) for option in q.options], marker="letter")
    if q.select == "multiple":
        # Иначе решающему неоткуда узнать, что верных ответов больше одного:
        # single и multiple рендерятся одинаковым списком.
        body = f'<div class="choice-hint">{t("choice_multiple_hint")}</div>' + body
    return body


def render_match(q: MatchModel) -> str:
    """Сопоставить. `right` — пул вариантов с явными `id` (дистракторы
    допустимы); `left[].match` — ссылка на `right[].id`, поэтому перестановки
    списков ничего не ломают."""
    left_html = list_html([esc(item.text) for item in q.left], marker="number")
    right_html = list_html([esc(item.text) for item in q.right], marker="letter")
    return f'<div class="match-columns">{left_html}{right_html}</div>'


def render_fill_text(q: FillTextModel) -> str:
    """Заполнить пропуск, носитель — текст. Плейсхолдер `___имя___` — ключ
    `blanks` (регэксп общий с валидацией — BLANK_RE в models.py)."""
    pieces = []
    last = 0
    for m in BLANK_RE.finditer(q.template):
        pieces.append(esc(q.template[last : m.start()]))
        pieces.append('<span class="fill-blank"></span>')
        last = m.end()
    pieces.append(esc(q.template[last:]))
    body = f'<p>{"".join(pieces)}</p>'
    if q.bank:
        body = bank_list(q.bank) + body
    return body


def render_fill_table(q: FillTableModel) -> str:
    """Заполнить пропуск, носитель — таблица. Форма `headers`/`rows` совпадает
    с компонентом `table`; ячейка-пропуск — `{"answer": …}` с ответом инлайн."""
    resolved_rows = []
    for row in q.rows:
        cells = [esc(cell) if isinstance(cell, str) else blank_cell() for cell in row]
        resolved_rows.append(cells)
    body = table_html([esc(h) for h in q.headers], resolved_rows)
    if q.bank:
        body = bank_list(q.bank) + body
    return body


def render_plot(q: PlotModel) -> str:
    """Построить график. `given` — серии, уже данные решающему на осях;
    `answer` — серии правильного ответа, рисуются в секции ответов."""
    return build_chart_svg(
        x_label=q.x_label,
        y_label=q.y_label,
        x_range=q.x_range,
        y_range=q.y_range,
        series=q.given or [],
        chart_type=q.chart_type,
    )


def _square(mark: str = "") -> str:
    return f'<span class="tf-square">{mark}</span>'


def render_true_false(q: TrueFalseModel) -> str:
    """Да/нет; правильные ответы — в секции ответов, по номерам утверждений."""
    items = []
    for statement in q.statements:
        items.append(
            '<span class="tf-line">'
            f'<span class="tf-statement">{esc(statement.text)}</span>'
            '<span class="tf-box">'
            f'{_square()} {t("true_label")}&nbsp;&nbsp;'
            f'{_square()} {t("false_label")}'
            "</span>"
            "</span>"
        )
    return list_html(items)


def render_rank(q: RankModel) -> str:
    """Упорядочивание. Порядок массива — порядок показа (перемешанный);
    `position` — правильная позиция инлайн у каждого пункта."""
    items = []
    for item in q.items:
        items.append(
            '<span class="tf-line">'
            f'<span class="tf-statement">{esc(item.text)}</span>'
            '<span class="rank-square"></span>'
            "</span>"
        )
    return list_html(items)


def render_classify(q: ClassifyModel) -> str:
    """Классифицировать. `category` — инлайн у каждого объекта; категория
    без объектов допустима (дистрактор)."""
    rows = [
        f'<span class="tf-line"><span class="tf-statement">{esc(item.text)}</span>{blank(115)}</span>'
        for item in q.items
    ]
    return list_html(rows)


# --- Ответы (компактная форма для секции «Ответы» в конце документа) ---

def answer_open(q: OpenModel) -> str:
    return esc(q.answer) if q.answer else ""


def answer_choice(q: ChoiceModel) -> str:
    # Буквы — те же а)/б), что реально напечатаны маркером списка вариантов:
    # источник букв один (strings.LETTERS).
    letters = [LETTERS[i] for i, option in enumerate(q.options) if option.correct]
    return esc(", ".join(letters))


def answer_match(q: MatchModel) -> str:
    # Печатная буква правого списка позиционная, связь — по id.
    id_to_letter = {item.id: LETTERS[j] for j, item in enumerate(q.right)}
    return esc(", ".join(
        f"{i + 1}-{id_to_letter[item.match]}" for i, item in enumerate(q.left)
    ))


def answer_fill_text(q: FillTextModel) -> str:
    # Значения пропусков в порядке появления в шаблоне.
    values = [q.blanks[m.group(1)] for m in BLANK_RE.finditer(q.template)]
    return esc("; ".join(values))


def answer_fill_table(q: FillTableModel) -> str:
    # Значения ячеек-пропусков в порядке чтения таблицы.
    values = [
        cell.answer for row in q.rows for cell in row if not isinstance(cell, str)
    ]
    return esc("; ".join(values))


def answer_plot(q: PlotModel) -> str:
    """Правильный график — мини-SVG теми же осями, что и тело вопроса."""
    return build_chart_svg(
        x_label=q.x_label,
        y_label=q.y_label,
        x_range=q.x_range,
        y_range=q.y_range,
        series=q.answer,
        chart_type=q.chart_type,
    )


def answer_true_false(q: TrueFalseModel) -> str:
    parts = [
        f"{i + 1} — {t('true_label') if s.answer else t('false_label')}"
        for i, s in enumerate(q.statements)
    ]
    return esc(", ".join(parts))


def answer_rank(q: RankModel) -> str:
    # Номера пунктов (в порядке показа) — в правильном порядке.
    order = sorted(range(len(q.items)), key=lambda i: q.items[i].position)
    return esc(", ".join(str(i + 1) for i in order))


def answer_classify(q: ClassifyModel) -> str:
    # Сводка по категориям в авторском порядке `categories`; пустая
    # категория показывается прочерком.
    groups = []
    for category in q.categories:
        texts = [item.text for item in q.items if item.category == category]
        groups.append(f"{category}: {', '.join(texts) if texts else '—'}")
    return esc("; ".join(groups))


QUESTION_BODY_RENDERERS: dict[type, Callable[..., str]] = {
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

QUESTION_ANSWER_RENDERERS: dict[type, Callable[..., str]] = {
    OpenModel: answer_open,
    ChoiceModel: answer_choice,
    MatchModel: answer_match,
    FillTextModel: answer_fill_text,
    FillTableModel: answer_fill_table,
    PlotModel: answer_plot,
    TrueFalseModel: answer_true_false,
    RankModel: answer_rank,
    ClassifyModel: answer_classify,
}


def render_question(q: QuestionModel) -> str:
    """Тело вопроса — то, что печатается в документе на месте задания."""
    return QUESTION_BODY_RENDERERS[type(q)](q)


def render_answer(q: QuestionModel) -> str:
    """Ответ вопроса для секции «Ответы»: HTML-безопасная компактная строка
    (или мини-SVG у plot); пустая строка — ответа нет (`open` без answer).
    `explanation` сюда не входит — его печатает сборщик секции ответов."""
    return QUESTION_ANSWER_RENDERERS[type(q)](q)
