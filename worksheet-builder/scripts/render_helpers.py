"""Мелкие текстовые хелперы, общие для рендереров компонентов и документа."""
import html
import re
import string

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


def _fill_blank_render(template, blanks, is_teacher):
    pieces = []
    last = 0
    for m in re.finditer(r"___(\w+)___", template):
        pieces.append(esc(template[last : m.start()]))
        key = m.group(1)
        if is_teacher and key in blanks:
            pieces.append(f'<span class="fill-blank answered">{esc(blanks[key])}</span>')
        else:
            pieces.append('<span class="fill-blank">&nbsp;</span>')
        last = m.end()
    pieces.append(esc(template[last:]))
    return "".join(pieces)
