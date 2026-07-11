"""Рендереры по формату компонента. Каждая функция render_* возвращает
(body_html, answer_html_или_None).

5 структурных форматов заменяют старые 15 семантических типов — сгруппированы
по тому, какую форму данных реально потребляет рендерер, а не по
педагогическому смыслу. Получает ли компонент букву (a/b/в...) и ответ для
тичер-версии, решает исключительно его собственный флаг `answerable` (см.
document.render_task()), а не то, каким форматом он рендерится.

Каждый render_* получает только `settings` — вложенный объект компонента
(`comp["settings"]`), без `type`/`answerable`/`prompt`/`points`/`label`. Это и
есть "компонент хранит только себя": формат-рендерер не видит и не должен
видеть общий протокол задания, только свои собственные данные, включая
собственный механизм ответа (`answer`/`answer_chart_spec`/`answers`/`correct`
на пунктах и т.п. — это тоже часть того, как формат хранит данные)."""

from render_helpers import esc, LETTERS, LOWER_LETTERS, _fill_blank_render
from strings import t
from visuals import build_chart_svg, _resolve_svg


def render_text(settings, is_teacher, lang):
    template = settings.get("text_template")
    if template is None:
        # Без пропусков в тексте: собственный prompt компонента (его рендерит
        # вызывающий код как строку заголовка) *и есть* содержимое — больше
        # нечего рендерить в теле. `answer` всё равно пробрасывается, как у
        # prompt_response/visual, — для чисто устного/дискуссионного вопроса,
        # которому нужна только заметка для учителя.
        return "", settings.get("answer")
    blanks = settings.get("blanks", {})
    return f"<p>{_fill_blank_render(template, blanks, is_teacher)}</p>", settings.get("answer")


def render_list(settings, is_teacher, lang):
    items = settings.get("items", [])
    style = settings.get("item_style", "plain")

    if style == "matching":
        # Сопоставление: те же `items`, что и у любого другого item_style
        # (каждый — `{"text", "match"}`), а не отдельная копия схемы через
        # `left_items`/`answer_map` — раньше режим определялся implicit-dispatch
        # по наличию `left_items`/`right_items`, что могло разойтись с `items`
        # (например, если оба поля заданы по ошибке, `items` тихо игнорировался).
        # `right_items` остаётся отдельным полем осознанно — это порядок/пул
        # показа правого столбца (может включать дистракторы, не встречающиеся
        # ни в одном `match`), а не то же самое, что можно вывести из `items`.
        right_items = settings.get("right_items", [])
        if not right_items:
            raise ValueError("list с item_style='matching' требует непустой right_items")
        letters = {value: LETTERS[i] for i, value in enumerate(right_items)}
        left_html = "".join(f"<li>{esc(it.get('text', ''))}</li>" for it in items)
        right_html = "".join(f"<li>{esc(value)}</li>" for value in right_items)
        body = (
            '<div class="matching-columns">'
            f'<ol type="1">{left_html}</ol>'
            f'<ol type="A" style="list-style-type: upper-latin;">{right_html}</ol>'
            "</div>"
        )
        pairs = []
        for i, it in enumerate(items, start=1):
            matched = it.get("match")
            if matched not in letters:
                raise ValueError(
                    f"list item_style='matching': match {matched!r} не найден в right_items"
                )
            pairs.append(f"{i}-{letters[matched]}")
        return body, ", ".join(pairs) if pairs else None

    if style == "ranking":
        # Тот же принцип "ответ на самом пункте", что у match/correct: `rank`
        # — верная позиция (1..N). Порядок показа — это порядок `items`,
        # авторский (обычно перемешанный) — рендерер намеренно не сортирует и
        # не перемешивает сам, чтобы результат оставался детерминированным
        # при перегенерации.
        missing = [it.get("text", "?") for it in items if not isinstance(it.get("rank"), int)]
        if missing:
            raise ValueError(f"list item_style='ranking': нет целого rank у пунктов: {missing}")
        ranks = [it["rank"] for it in items]
        if sorted(ranks) != list(range(1, len(items) + 1)):
            raise ValueError(
                f"list item_style='ranking': rank должен быть перестановкой 1..{len(items)}, получено {ranks}"
            )
        rows = []
        for it in items:
            box = str(it["rank"]) if is_teacher else ""
            rows.append(
                '<div class="rank-row">'
                f'<span class="rank-statement">{esc(it.get("text", ""))}</span>'
                f'<span class="rank-square">{box}</span>'
                "</div>"
            )
        return "".join(rows), None

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
        layout = settings.get("variants_layout", "single-column")
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
        return body, settings.get("answer")

    # "plain" — голый маркированный/нумерованный список, без отметок правильности (информационный).
    tag = "ol" if settings.get("ordered") else "ul"
    items_html = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<{tag}>{items_html}</{tag}>", None


def render_table(settings, is_teacher, lang):
    # Ячейка `null` = пустое место для заполнения, раскрывается через
    # `answers["r,c"]` в тичер-версии; таблица без `null`-ячеек — это просто
    # обычная справочная таблица (информационная) — один код обслуживает оба случая.
    headers = settings.get("headers", [])
    rows = settings.get("rows", [])
    answers = settings.get("answers", {})
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


def render_prompt_response(settings, is_teacher, lang):
    response = str(settings.get("response", "none"))
    if response.startswith("lines:"):
        lines = int(response.split(":", 1)[1])
        show_response = settings.get("show_response", True)
        style = ' style="display:none;"' if not show_response else ""
        body = f'<div class="solution-area"{style}>' + "".join(
            '<div class="solution-line"></div>' for _ in range(lines)
        ) + "</div>"
    elif response == "blank":
        body = f'<div>{t(lang, "answer_label")} <span class="answer-line"></span></div>'
    else:
        body = ""
    return body, settings.get("answer")


def render_visual(settings, is_teacher, lang):
    # Ровно одно из chart_spec / svg_snippet / raw_svg должно задавать
    # основной визуал, и опционально одно из answer_chart_spec /
    # answer_svg_snippet / answer_raw_svg — второй, только-тичер визуал
    # (старые chart/chart_fill и illustration/illustration_draw были четырьмя
    # типами вокруг этой же формы "источник + опциональный источник ответа" —
    # здесь объединены в один диспетчер, имена полей не менялись). Без
    # источника вообще — рендерится пустая рамка (например, для свободного
    # рисования схемы самим учеником).
    if is_teacher and "answer_chart_spec" in settings:
        return build_chart_svg(settings["answer_chart_spec"]), settings.get("answer")
    if "chart_spec" in settings:
        return build_chart_svg(settings["chart_spec"]), settings.get("answer")

    if is_teacher:
        svg = _resolve_svg(settings, "answer_svg_snippet", "answer_raw_svg") or _resolve_svg(settings, "svg_snippet", "raw_svg")
    else:
        svg = _resolve_svg(settings, "svg_snippet", "raw_svg")
    body = f'<div class="illustration-wrap">{svg}</div>' if svg else '<div class="illustration-blank"></div>'
    return body, settings.get("answer")


COMPONENT_RENDERERS = {
    "text": render_text,
    "list": render_list,
    "table": render_table,
    "prompt_response": render_prompt_response,
    "visual": render_visual,
}
