"""Мелкие текстовые хелперы, общие для рендера компонентов (components.py)
и вопросов (questions.py) — см. references/document-schema.md. Экранирование:
`esc()` эскейпит сырой авторский текст в точке интерполяции;
`blank`/`blank_cell`/`bank_list` сами строят готовую, уже
HTML-безопасную разметку ("пропуск в строке") и не знают ничего о конкретном
вопросе. Разлинованное место под ответ — не здесь, а компонентом `paper`
(paper.py): у него есть данные и своя модель. `fmt_num`/`svg_label` — общие хелперы SVG-генераторов
(visuals.py, instruments.py): единый формат чисел и подписей на всех
артефактах документа (см. references/artifacts/README.md)."""
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


def fmt_num(n: float) -> str:
    """Единый формат чисел на шкалах/осях всех SVG-артефактов: целые без
    `.0`, дроби без хвостовых нулей и без float-шума (0.30000000000000004)."""
    if abs(n - round(n)) < 1e-9:
        return str(int(round(n)))
    return f"{n:.2f}".rstrip("0").rstrip(".")


def svg_label(raw: str) -> str:
    """Текст подписи для SVG-контекста: `esc()` пропускает буквальные
    `<sup>`/`<sub>`, но внутри SVG `<text>` HTML-теги невалидны и молча
    ломают отрисовку — конвертируем их в `<tspan>` со сдвигом базовой
    линии."""
    escaped = esc(raw)
    escaped = escaped.replace("<sup>", '<tspan baseline-shift="super" font-size="7">')
    escaped = escaped.replace("<sub>", '<tspan baseline-shift="sub" font-size="7">')
    escaped = escaped.replace("</sup>", "</tspan>").replace("</sub>", "</tspan>")
    return escaped


def blank(width_px: int = 150) -> str:
    """Короткая подчёркнутая линия для ответа в строку (`response: 'blank'`)."""
    return f'<span class="answer-line" style="min-width:{width_px}px;"></span>'


def blank_cell() -> str:
    """Пустая ячейка-заглушка для таблицы (тот же визуальный язык "пропуска",
    что и `fill-blank` в тексте, а не голый `&nbsp;`)."""
    return '<span class="fill-blank"></span>'


def bank_list(items: list[str]) -> str:
    """"Слова/категории для выбора: ..." списком (для fill_text/fill_table)."""
    joined = ", ".join(esc(item) for item in items)
    return f'<div class="bank-list"><strong>{t("bank_label")}</strong> {joined}</div>'
