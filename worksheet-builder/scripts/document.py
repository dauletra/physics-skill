"""Собирает одно задание и весь HTML-документ из meta.json + заданий."""

from assets import BASE_CSS, KATEX_HEAD, LAYOUT_JS
from components import COMPONENT_RENDERERS, render_layout_toolbar
from render_helpers import esc, LOWER_LETTERS
from strings import STRINGS, t


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


def render_header_line(num_html, prompt, points, lang):
    # Номер/буква и текст prompt сидят на одной строке (num_html не оборачивается,
    # поэтому строки переноса виснут с отступом под текстом, а не под номером);
    # баллы рендерятся инлайн в конце текста, а не рядом с номером — по правилам
    # нумерации из design-system.md.
    points_html = f' <span class="task-points">({esc(points)} {t(lang, "points_suffix")})</span>' if points else ""
    if prompt:
        prompt_html = f'<span class="task-prompt">{esc(prompt)}{points_html}</span>'
    elif points_html:
        prompt_html = f'<span class="task-prompt">{points_html.strip()}</span>'
    else:
        prompt_html = ""
    return f'<div class="task-header">{num_html}{prompt_html}</div>'


def _partition_layout(components, layout):
    # По умолчанию: каждый компонент в своей полноширинной строке (сегодняшний
    # вид "всё в столбик"). Иначе каждый элемент — либо целое N (N равных
    # колонок), либо список явных процентов (по одному на колонку) — см.
    # "Раскладка: layout" в task-schema.md. Проверяется простой арифметикой:
    # партиция обязана учесть ровно каждый компонент, никаких адресуемых ячеек,
    # которые могли бы разъехаться.
    if not layout:
        return [1] * len(components)
    total = sum(row if isinstance(row, int) else len(row) for row in layout)
    if total != len(components):
        raise ValueError(
            f"layout describes {total} component(s) but there are {len(components)}"
        )
    return layout


def render_task(index, task, is_teacher, lang):
    components = task.get("components", [])
    if not components:
        raise ValueError(f"Task {task.get('id')} has no components")

    answerable_positions = [i for i, c in enumerate(components) if c.get("answerable")]
    # Буквы имеют смысл, только когда отвечать нужно больше чем на одно —
    # одинокий отвечаемый компонент читается как простое обычное задание, без
    # буквы — ЕСЛИ ТОЛЬКО автор явно не задал на нём `label`, а это всегда
    # побеждает. Автогенерируемые буквы пропускают любое значение, уже занятое
    # явным `label` где-то ещё в этом задании, так что более поздняя автобуква
    # не столкнётся с более ранней явной (например, явный "label": "z" на
    # компоненте 0 не должен привести к тому, что компонент 1 получит авто
    # "b" — он должен получить "a").
    explicit_labels = {
        components[pos]["label"] for pos in answerable_positions if components[pos].get("label")
    }
    auto_letters = iter(l for l in LOWER_LETTERS if l not in explicit_labels)
    letter_for = {}
    if len(answerable_positions) > 1 or explicit_labels:
        for pos in answerable_positions:
            explicit = components[pos].get("label")
            letter_for[pos] = explicit if explicit else next(auto_letters)

    task_prompt = task.get("prompt", "")
    task_points = task.get("points")
    # Единственный компонент без вступления на уровне задания читается ровно
    # как сегодняшнее простое плоское задание: его собственные prompt/points
    # сливаются в одну строку заголовка с номером задания, вместо двух
    # стопкой строк заголовка ради одного вопроса.
    single_component = len(components) == 1 and not task_prompt

    rows = _partition_layout(components, task.get("layout"))
    row_htmls = []
    if not single_component:
        # Вступление на уровне задания (номер + prompt) само по себе является
        # компонентом для целей раскладки — по умолчанию оно получает свою
        # полноширинную строку 0, как и любой другой компонент, так что
        # hover-контролы +/- (initRowControls в LAYOUT_JS) могут смёрстить его
        # с соседней строкой тоже, а не только переставлять "настоящие"
        # JSON-компоненты после него.
        header_html = render_header_line(f'<span class="task-num">{index}.</span>', task_prompt, task_points, lang)
        row_htmls.append(
            f'<div class="task-row"><div class="task-col" data-role="header" style="flex:0 0 100%;max-width:100%;">{header_html}</div></div>'
        )

    idx = 0
    for row in rows:
        width = row if isinstance(row, int) else len(row)
        pct_list = [100.0 / width] * width if isinstance(row, int) else row
        cell_htmls = []
        for cell_i in range(width):
            comp = components[idx]
            ctype = comp.get("type")
            renderer = COMPONENT_RENDERERS.get(ctype)
            if renderer is None:
                raise ValueError(
                    f"Unknown component type '{ctype}' in task {task.get('id')} (component {idx})"
                )
            body_html, answer = renderer(comp, is_teacher, lang)

            comp_prompt = comp.get("prompt", "")
            comp_points = comp.get("points")
            # В letter_for есть записи только для отвечаемых позиций, так что
            # само наличие ключа уже означает, что компонент отвечаемый — см. его построение выше.
            label = letter_for.get(idx) if not single_component else None

            if single_component:
                num_html = f'<span class="task-num">{index}.</span>'
                merged_points = comp_points if comp_points is not None else task_points
                header_html = render_header_line(num_html, comp_prompt, merged_points, lang)
            elif label:
                header_html = render_header_line(
                    f'<span class="subtask-label">{esc(label)})</span>', comp_prompt, comp_points, lang
                )
            elif comp_prompt or comp_points:
                header_html = render_header_line("", comp_prompt, comp_points, lang)
            else:
                header_html = ""

            answer_html = ""
            if is_teacher and answer:
                answer_html = f'<div class="answer-block"><strong>{t(lang, "answer_label")}</strong> {esc(answer)}</div>'

            toolbar_html = render_layout_toolbar(comp)
            comp_class = "task-component task-component-lettered" if label else "task-component"
            pct = pct_list[cell_i]
            cell_htmls.append(
                f'<div class="task-col" style="flex:0 0 {pct:.2f}%;max-width:{pct:.2f}%;">'
                f'<div class="{comp_class}">{header_html}{body_html}{answer_html}{toolbar_html}</div>'
                "</div>"
            )
            idx += 1
        row_htmls.append(f'<div class="task-row">{"".join(cell_htmls)}</div>')

    components_html = f'<div class="task-components">{"".join(row_htmls)}</div>'

    return f'<div class="task">{components_html}</div>'


def build_document(meta, tasks, is_teacher):
    lang = meta.get("language", "ru")
    body = [render_header(meta)]
    for i, task in enumerate(tasks, start=1):
        body.append(render_task(i, task, is_teacher, lang))
    variant = t(lang, "teacher_variant") if is_teacher else t(lang, "student_variant")
    js_lang = lang if lang in STRINGS else "ru"
    return f"""<!DOCTYPE html>
<html lang="{js_lang}">
<head>
<meta charset="UTF-8">
<title>{esc(meta.get('title') or t(lang, "default_title"))} — {variant}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{''.join(body)}
<script>const WORKSHEET_LANG = "{js_lang}";
{LAYOUT_JS}</script>
</body>
</html>"""
