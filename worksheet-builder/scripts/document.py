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


def render_header_line(num_html, prompt_component, points, lang):
    # Номер/буква и текст prompt сидят на одной строке (num_html не оборачивается,
    # поэтому строки переноса виснут с отступом под текстом, а не под номером);
    # баллы рендерятся инлайн в конце текста, а не рядом с номером — по правилам
    # нумерации из design-system.md. `prompt_component` — TextComponent (или None,
    # если у этой строки заголовка вообще нет вопроса) — берём уже готовый,
    # эскейпнутый `.body`, эскейпинг здесь больше не делается повторно.
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    body = prompt_component.body if prompt_component else ""
    if body:
        prompt_html = f'<p class="task-prompt">{body}{points_html}</p>'
    elif points_html:
        prompt_html = f'<p class="task-prompt">{points_html.strip()}</p>'
    else:
        prompt_html = ""
    return f'<div class="task-header">{num_html}{prompt_html}</div>'


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
    # Единственный вопрос без раздельных компонентов-стимулов читается ровно
    # как сегодняшнее простое плоское задание: его собственные prompt/points
    # сливаются в одну строку заголовка с номером задания, вместо отдельной
    # строки-заголовка задания над одиноким вопросом.
    single_item_question = len(items) == 1 and isinstance(items[0], Question)

    rows = partition_layout(items, task.layout)
    row_htmls = []
    if not single_item_question:
        header_html = render_header_line(f'<span class="task-num">{index}.</span>', None, task_points, lang)
        row_htmls.append(
            f'<div class="task-row"><div class="task-col" data-role="header" style="flex:0 0 100%;max-width:100%;">{header_html}</div></div>'
        )

    idx = 0
    for row in rows:
        width = row if isinstance(row, int) else len(row)
        pct_list = [100.0 / width] * width if isinstance(row, int) else row
        cell_htmls = []
        for cell_i in range(width):
            item = items[idx]

            if isinstance(item, Question):
                if single_item_question:
                    num_html = f'<span class="task-num">{index}.</span>'
                    merged_points = item.points if item.points is not None else task_points
                    header_html = render_header_line(num_html, item.prompt, merged_points, lang)
                elif item.label:
                    header_html = render_header_line(
                        f'<span class="subtask-label">{esc(item.label)})</span>', item.prompt, item.points, lang
                    )
                elif item.prompt.body or item.points:
                    header_html = render_header_line("", item.prompt, item.points, lang)
                else:
                    header_html = ""
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
