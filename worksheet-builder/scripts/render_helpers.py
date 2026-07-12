"""Мелкие текстовые хелперы, общие для чистых компонентов (уровень 2) и
классов вопросов (уровень 3) — см. references/task-schema.md. Экранирование:
`esc()` эскейпит сырой авторский текст; `lines`/`blank`/`blank_cell`/
`answer_block`/`bank_list` сами строят готовую, уже HTML-безопасную разметку
("место под ответ") и не знают ничего о конкретном вопросе."""
import html
import string

from strings import t

LETTERS = string.ascii_uppercase
LOWER_LETTERS = string.ascii_lowercase

SUPSUB_TAGS = ("sup", "sub")


def esc(text):
    # Экранирует всё, кроме буквальных <sup>/<sub> (и их закрывающих тегов),
    # чтобы JSON задания мог использовать их для индексов/степеней без
    # юникодного символа (см. references/symbols.md), не открывая при этом
    # произвольный HTML.
    escaped = html.escape(str(text if text is not None else ""))
    for tag in SUPSUB_TAGS:
        escaped = escaped.replace(f"&lt;{tag}&gt;", f"<{tag}>")
        escaped = escaped.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    return escaped


def lines(n):
    """N разлинованных строк под решение (открытый вопрос, `response: 'lines:N'`)."""
    return '<div class="solution-area">' + "".join(
        '<div class="solution-line"></div>' for _ in range(n)
    ) + "</div>"


def blank(width_mm=40):
    """Короткая подчёркнутая линия для ответа в строку (`response: 'blank'`)."""
    return f'<span class="answer-line" style="min-width:{width_mm}mm;"></span>'


def blank_cell():
    """Пустая ячейка-заглушка для таблицы (тот же визуальный язык "пропуска",
    что и `fill-blank` в тексте, а не голый `&nbsp;`)."""
    return '<span class="fill-blank"></span>'


def answer_block(lang, text):
    """Тичер-only рамка "Ответ: ..." под условием."""
    return f'<div class="answer-block"><strong>{t(lang, "answer_label")}</strong> {esc(text)}</div>'


def bank_list(lang, items):
    """"Слова/категории для выбора: ..." списком (для fill_text/fill_table)."""
    joined = ", ".join(esc(item) for item in items)
    return f'<div class="bank-list"><strong>{t(lang, "bank_label")}</strong> {joined}</div>'
