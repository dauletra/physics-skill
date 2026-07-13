"""Мелкие текстовые хелперы, общие для рендера компонентов (components.py)
и вопросов (questions.py) — см. references/task-schema.md. Экранирование:
`esc()` эскейпит сырой авторский текст в точке интерполяции; `lines`/
`blank`/`blank_cell`/`answer_block`/`bank_list` сами строят готовую, уже
HTML-безопасную разметку ("место под ответ") и не знают ничего о конкретном
вопросе."""
import html

from worksheet_builder.strings import t

SUPSUB_TAGS = ("sup", "sub")


def esc(text: object) -> str:
    # Экранирует всё, кроме буквальных <sup>/<sub> (и их закрывающих тегов),
    # чтобы JSON задания мог использовать их для индексов/степеней без
    # юникодного символа (см. references/symbols.md), не открывая при этом
    # произвольный HTML.
    escaped = html.escape(str(text if text is not None else ""))
    for tag in SUPSUB_TAGS:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


def lines(n: int) -> str:
    """N разлинованных строк под решение (открытый вопрос, `response: 'lines:N'`)."""
    return '<div class="solution-area">' + "".join(
        '<div class="solution-line"></div>' for _ in range(n)
    ) + "</div>"


def blank(width_px: int = 150) -> str:
    """Короткая подчёркнутая линия для ответа в строку (`response: 'blank'`)."""
    return f'<span class="answer-line" style="min-width:{width_px}px;"></span>'


def blank_cell() -> str:
    """Пустая ячейка-заглушка для таблицы (тот же визуальный язык "пропуска",
    что и `fill-blank` в тексте, а не голый `&nbsp;`)."""
    return '<span class="fill-blank"></span>'


def answer_block(text: str, label_key: str = "answer_label") -> str:
    """Тичер-only рамка "Ответ: ..." (или "Пояснение: ..." для
    `explanation` — см. Question.render) под условием."""
    return f'<div class="answer-block"><strong>{t(label_key)}</strong> {esc(text)}</div>'


def bank_list(items: list[str]) -> str:
    """"Слова/категории для выбора: ..." списком (для fill_text/fill_table)."""
    joined = ", ".join(esc(item) for item in items)
    return f'<div class="bank-list"><strong>{t("bank_label")}</strong> {joined}</div>'
