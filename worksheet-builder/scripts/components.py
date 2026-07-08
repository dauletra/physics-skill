"""Рендереры по формату компонента. Каждая функция render_* возвращает
(body_html, answer_html_или_None).

5 структурных форматов заменяют старые 15 семантических типов — сгруппированы
по тому, какую форму данных реально потребляет рендерер, а не по
педагогическому смыслу. Получает ли компонент букву (a/b/в...) и ответ для
тичер-версии, решает исключительно его собственный флаг `answerable` (см.
document.render_task()), а не то, каким форматом он рендерится."""

from render_helpers import esc, LETTERS, LOWER_LETTERS, _fill_blank_render
from strings import t
from visuals import build_chart_svg, _resolve_svg


def render_text(task, is_teacher, lang):
    template = task.get("text_template")
    if template is None:
        # Без пропусков в тексте: собственный prompt компонента (его рендерит
        # вызывающий код как строку заголовка) *и есть* содержимое — больше
        # нечего рендерить в теле. `answer` всё равно пробрасывается, как у
        # prompt_response/visual, — для чисто устного/дискуссионного вопроса,
        # которому нужна только заметка для учителя.
        return "", task.get("answer")
    blanks = task.get("blanks", {})
    return f"<p>{_fill_blank_render(template, blanks, is_teacher)}</p>", task.get("answer")


def render_list(task, is_teacher, lang):
    # Двухколоночный режим (старый `matching`): `left_items`/`right_items`
    # полностью заменяют `items`, взаимоисключающе с одноколоночными режимами ниже.
    if "left_items" in task or "right_items" in task:
        left_items = task.get("left_items", [])
        right_items = task.get("right_items", [])
        answer_map = task.get("answer_map", {})
        left_html = "".join(f"<li>{esc(item)}</li>" for item in left_items)
        letters = {item: LETTERS[i] for i, item in enumerate(right_items)}
        right_html = "".join(f"<li>{esc(item)}</li>" for item in right_items)
        body = (
            '<div class="matching-columns">'
            f'<ol type="1">{left_html}</ol>'
            f'<ol type="A" style="list-style-type: upper-latin;">{right_html}</ol>'
            "</div>"
        )
        answer = None
        if answer_map:
            pairs = []
            for i, item in enumerate(left_items, start=1):
                matched = answer_map.get(item)
                letter = letters.get(matched, "?")
                pairs.append(f"{i}-{letter}")
            answer = ", ".join(pairs)
        return body, answer

    items = task.get("items", [])
    style = task.get("item_style", "plain")

    if style == "statement_bool":
        rows = []
        for it in items:
            text = esc(it.get("text", ""))
            correct = it.get("correct")
            true_mark = "&#10005;" if is_teacher and correct is True else ""
            false_mark = "&#10005;" if is_teacher and correct is False else ""
            rows.append(
                '<div class="tf-row">'
                f'<span class="tf-statement">{text}</span>'
                '<span class="tf-box">'
                f'<span class="tf-square">{true_mark}</span> {t(lang, "true_label")}&nbsp;&nbsp;'
                f'<span class="tf-square">{false_mark}</span> {t(lang, "false_label")}'
                "</span>"
                "</div>"
            )
        return "".join(rows), None

    if style == "choice":
        layout = task.get("variants_layout", "single-column")
        parts = []
        for i, it in enumerate(items):
            is_correct = is_teacher and bool(it.get("correct"))
            mark = "&#10003;" if is_correct else ""
            css = "mc-option mc-correct" if is_correct else "mc-option"
            parts.append(
                f'<span class="{css}"><span class="mc-marker">{mark}</span> '
                f'{LOWER_LETTERS[i]}) {esc(it.get("text", ""))}</span>'
            )
        body = f'<div class="mc-options mc-layout-{esc(layout)}">' + "".join(parts) + "</div>"
        return body, task.get("answer")

    # "plain" — голый маркированный/нумерованный список, без отметок правильности (информационный).
    tag = "ol" if task.get("ordered") else "ul"
    items_html = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<{tag}>{items_html}</{tag}>", None


def render_table(task, is_teacher, lang):
    # Ячейка `null` = пустое место для заполнения, раскрывается через
    # `answers["r,c"]` в тичер-версии; таблица без `null`-ячеек — это просто
    # обычная справочная таблица (информационная) — один код обслуживает оба случая.
    headers = task.get("headers", [])
    rows = task.get("rows", [])
    answers = task.get("answers", {})
    thead = "".join(f"<th>{esc(h)}</th>" for h in headers)
    body_rows = []
    for r_i, row in enumerate(rows):
        cells = []
        for c_i, cell in enumerate(row):
            if cell is None:
                key = f"{r_i},{c_i}"
                value = answers.get(key, "") if is_teacher else ""
                cells.append(f'<td>{esc(value)}</td>' if value else "<td>&nbsp;</td>")
            else:
                cells.append(f"<td>{esc(cell)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    table = (
        '<table class="fill-table">'
        f"<thead><tr>{thead}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody>"
        "</table>"
    )
    return table, None


def render_prompt_response(task, is_teacher, lang):
    response = str(task.get("response", "none"))
    if response.startswith("lines:"):
        lines = int(response.split(":", 1)[1])
        show_response = task.get("show_response", True)
        style = ' style="display:none;"' if not show_response else ""
        body = f'<div class="solution-area"{style}>' + "".join(
            '<div class="solution-line"></div>' for _ in range(lines)
        ) + "</div>"
    elif response == "blank":
        body = f'<div>{t(lang, "answer_label")} <span class="answer-line"></span></div>'
    else:
        body = ""
    return body, task.get("answer")


def render_visual(task, is_teacher, lang):
    # Ровно одно из chart_spec / svg_snippet / raw_svg должно задавать
    # основной визуал, и опционально одно из answer_chart_spec /
    # answer_svg_snippet / answer_raw_svg — второй, только-тичер визуал
    # (старые chart/chart_fill и illustration/illustration_draw были четырьмя
    # типами вокруг этой же формы "источник + опциональный источник ответа" —
    # здесь объединены в один диспетчер, имена полей не менялись). Без
    # источника вообще — рендерится пустая рамка (например, для свободного
    # рисования схемы самим учеником).
    if is_teacher and "answer_chart_spec" in task:
        return build_chart_svg(task["answer_chart_spec"]), task.get("answer")
    if "chart_spec" in task:
        return build_chart_svg(task["chart_spec"]), task.get("answer")

    if is_teacher:
        svg = _resolve_svg(task, "answer_svg_snippet", "answer_raw_svg") or _resolve_svg(task, "svg_snippet", "raw_svg")
    else:
        svg = _resolve_svg(task, "svg_snippet", "raw_svg")
    body = f'<div class="illustration-wrap">{svg}</div>' if svg else '<div class="illustration-blank"></div>'
    return body, task.get("answer")


COMPONENT_RENDERERS = {
    "text": render_text,
    "list": render_list,
    "table": render_table,
    "prompt_response": render_prompt_response,
    "visual": render_visual,
}


# Какие группы контролов экранного layout-тулбара (см. assets.LAYOUT_JS)
# применимы к компоненту. Ключуется по всему компоненту (не только по `type`),
# потому что один формат теперь покрывает несколько старых типов, из которых
# тулбар нужен не всем: чтобы подключить новый, добавь условие здесь плюс
# соответствующую запись CONTROL_GROUPS в LAYOUT_JS, чей селектор `target`
# совпадает с элементом, который рендерер этого формата уже выводит.
# (Per-row контролы колонок — отдельный механизм, они строятся безусловно на
# каждое задание через initRowControls() в LAYOUT_JS, не через эту функцию.)
def render_layout_toolbar(comp):
    controls = []
    if comp.get("type") == "prompt_response" and str(comp.get("response", "")).startswith("lines:"):
        controls.append("solution-toggle")
    if comp.get("type") == "list" and comp.get("item_style") == "choice":
        controls.append("variants-layout")
    if not controls:
        return ""
    return f'<div class="layout-toolbar" data-controls="{",".join(controls)}"></div>'
