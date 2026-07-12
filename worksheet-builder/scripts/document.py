"""Собирает одно задание и весь HTML-документ из meta.json + заданий."""

from assets import build_base_css, KATEX_HEAD, LAYOUT_JS
from layout import partition_layout
from questions.base import Question
from render_helpers import esc, LOWER_LETTERS
from strings import STRINGS, t
from task import Task


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
    # живёт как обычный `text`-элемент в `Task.items` (см. task-schema.md).
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    return f'<div class="task-header"><span class="task-num">{index}.</span>{points_html}</div>'


def render_label_line(label, points, lang):
    # Маленькая строка только из буквы вопроса и/или его баллов — без текста
    # (текст вопроса, если он есть, — отдельный `text`-элемент перед этим
    # вопросом в `items`, никак не связанный с этой строкой на уровне разметки).
    # Пусто, если ни буквы, ни баллов нет.
    label_html = f'<span class="subtask-label">{esc(label)})</span>' if label else ""
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    if not label_html and not points_html:
        return ""
    return f'<div class="task-header">{label_html}{points_html}</div>'


def render_task(index, task: Task, is_teacher, lang):
    items = task.items
    if not items:
        raise ValueError(f"Task {task.id} has no items")

    mode = "teacher" if is_teacher else "student"

    question_positions = [i for i, it in enumerate(items) if isinstance(it, Question)]
    # Буквы имеют смысл, только когда отвечать нужно больше чем на один вопрос
    # — одинокий вопрос читается как простое обычное задание, без буквы, ЕСЛИ
    # ТОЛЬКО автор явно не задал на нём `label`, а это всегда побеждает.
    # Автогенерируемые буквы пропускают любое значение, уже занятое явным
    # `label` где-то ещё в этом задании (см. "Буквы и баллы" в task-schema.md).
    explicit_labels = {items[pos].label for pos in question_positions if items[pos].label}
    auto_letters = iter(l for l in LOWER_LETTERS if l not in explicit_labels)
    if len(question_positions) > 1 or explicit_labels:
        for pos in question_positions:
            question = items[pos]
            if not question.label:
                question.label = next(auto_letters)

    task_points = task.points
    # Номер задания — всегда своя отдельная строка сверху (см.
    # render_task_number_line): описательный текст, если есть, живёт как
    # обычный `text`-элемент в items, а не мержится с этой строкой.
    rows = partition_layout(items, task.layout)
    header_html = render_task_number_line(index, task_points, lang)
    row_htmls = [
        f'<div class="task-row"><div class="task-col" data-role="header" style="flex:0 0 100%;max-width:100%;">{header_html}</div></div>'
    ]

    idx = 0
    for row in rows:
        width = row if isinstance(row, int) else len(row)
        pct_list = [100.0 / width] * width if isinstance(row, int) else row
        cell_htmls = []
        for cell_i in range(width):
            item = items[idx]

            if isinstance(item, Question):
                header_html = render_label_line(item.label, item.points, lang)
                body_html = item.render(mode, lang)
                comp_class = "task-component task-component-lettered" if item.label else "task-component"
                cell_html = f'<div class="{comp_class}">{header_html}{body_html}</div>'
            else:
                cell_html = f'<div class="task-component">{item.render()}</div>'

            pct = pct_list[cell_i]
            cell_htmls.append(
                f'<div class="task-col" style="flex:0 0 {pct:.2f}%;max-width:{pct:.2f}%;">{cell_html}</div>'
            )
            idx += 1
        row_htmls.append(f'<div class="task-row">{"".join(cell_htmls)}</div>')

    components_html = f'<div class="task-components">{"".join(row_htmls)}</div>'

    return f'<div class="task">{components_html}</div>'


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
