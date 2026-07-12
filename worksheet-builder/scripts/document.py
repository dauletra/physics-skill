"""Собирает одно задание и весь HTML-документ из meta.json + заданий."""

from assets import build_base_css, KATEX_HEAD, LAYOUT_JS
from questions.base import Question
from render_helpers import esc, LOWER_LETTERS
from strings import STRINGS, t
from task import iter_flat, Part, Row, Task

ROW_GAP_MM = 6.0  # должен совпадать с `gap` у .task-row в BASE_CSS


def render_header(meta):
    lang = meta.get("language", "ru")
    school = esc(meta.get("school") or "")
    date = esc(meta.get("date") or "")
    subject = esc(meta.get("subject", ""))
    grade = esc(meta.get("grade", ""))
    title = esc(meta.get("title", ""))
    instructions = meta.get("instructions")
    parts = ['<div class="sheet-header">']
    parts.append(
        f'<div class="meta-line">{t(lang, "school_class")} <span class="blank">{school}</span>'
        f' {t(lang, "date")} <span class="blank">{date}</span>'
        f' {t(lang, "full_name")} <span class="blank" style="min-width:60mm;"></span></div>'
    )
    parts.append(f'<div class="sheet-title">{title}</div>')
    parts.append(f'<div class="sheet-subtitle">{subject} &middot; {grade} {t(lang, "grade_suffix")}</div>')
    if instructions:
        parts.append(f'<div class="sheet-instructions">{esc(instructions)}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_task_number_line(index, points, lang):
    # Номер задания — всегда своя отдельная строка сверху, с баллами задания,
    # если они заданы. Описательный текст задания — не часть этой строки: он
    # живёт как обычный `text`-блок в `blocks` (см. task-schema.md).
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    return f'<div class="task-header"><span class="task-num">{index}.</span>{points_html}</div>'


def render_label_line(label, points, lang):
    # Маленькая строка только из буквы подзадания и/или его баллов — без
    # текста (условие подзадания — обычный `text`-блок внутри `part`).
    # Пусто, если ни буквы, ни баллов нет.
    label_html = f'<span class="subtask-label">{esc(label)})</span>' if label else ""
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    if not label_html and not points_html:
        return ""
    return f'<div class="task-header">{label_html}{points_html}</div>'


def assign_part_labels(parts):
    # Буква = part, по порядку следования. Явный `label` побеждает; авто-буквы
    # пропускают любое значение, уже занятое явным label (см. task-schema.md).
    explicit_labels = {part.label for part in parts if part.label}
    auto_letters = iter(l for l in LOWER_LETTERS if l not in explicit_labels)
    for part in parts:
        if not part.label:
            part.label = next(auto_letters)


def render_leaf(block, mode, lang):
    body = block.render(mode, lang) if isinstance(block, Question) else block.render()
    return f'<div class="task-block">{body}</div>'


def render_part(part: Part, mode, lang):
    header_html = render_label_line(part.label, part.points, lang)
    inner = "".join(render_block(block, mode, lang) for block in part.blocks)
    return f'<div class="task-part">{header_html}{inner}</div>'


def render_row(row: Row, mode, lang):
    # Ширины: либо инлайновые `width` у всех детей (парсер гарантирует
    # все-или-никто, сумма <= 100 — остаток строки остаётся пустым), либо
    # равное деление. flex-basis считается через calc с вычетом
    # пропорциональной доли межколоночного gap, чтобы 50+50 не переполняли
    # строку.
    n = len(row.blocks)
    widths = [b.width for b in row.blocks]
    if widths[0] is None:
        widths = [100.0 / n] * n
    cols = []
    for block, width in zip(row.blocks, widths):
        gap_share = ROW_GAP_MM * (n - 1) * width / 100.0
        basis = f"calc({width:.2f}% - {gap_share:.2f}mm)" if n > 1 else f"{width:.2f}%"
        cols.append(
            f'<div class="task-col" style="flex:0 1 {basis};max-width:{basis};">'
            f"{render_block(block, mode, lang)}</div>"
        )
    return f'<div class="task-row">{"".join(cols)}</div>'


def render_block(block, mode, lang):
    if isinstance(block, Row):
        return render_row(block, mode, lang)
    if isinstance(block, Part):
        return render_part(block, mode, lang)
    return render_leaf(block, mode, lang)


def render_task(index, task: Task, is_teacher, lang):
    mode = "teacher" if is_teacher else "student"

    # Буквы — по сплющенному обходу: part внутри row получает букву так же,
    # как получал бы, стоя на уровне задания (row прозрачен, см. task.py).
    assign_part_labels([b for b in iter_flat(task.blocks) if isinstance(b, Part)])

    # Номер задания — всегда своя отдельная строка сверху (см.
    # render_task_number_line).
    block_htmls = [render_task_number_line(index, task.points, lang)]
    for block in task.blocks:
        block_htmls.append(render_block(block, mode, lang))

    return f'<div class="task"><div class="task-blocks">{"".join(block_htmls)}</div></div>'


def build_document(meta, tasks, is_teacher):
    lang = meta.get("language", "ru")
    body = [render_header(meta)]
    for i, raw_task in enumerate(tasks, start=1):
        task = Task.from_dict(raw_task)
        body.append(render_task(i, task, is_teacher, lang))
    variant = t(lang, "teacher_variant") if is_teacher else t(lang, "student_variant")
    js_lang = lang if lang in STRINGS else "ru"
    css = build_base_css(meta.get("print_margins", "default"))
    return f"""<!DOCTYPE html>
<html lang="{js_lang}">
<head>
<meta charset="UTF-8">
<title>{esc(meta.get('title') or t(lang, "default_title"))} — {variant}</title>
{KATEX_HEAD}
<style>{css}</style>
</head>
<body>
{''.join(body)}
<script>{LAYOUT_JS}</script>
</body>
</html>"""
