"""Собирает одно задание и весь HTML-документ из моделей (models.py):
`MetaModel` + список `TaskModel`. Контейнеры (`part`/`row`) рендерятся
здесь; листья уходят в render_component/render_question."""

import json
from typing import Any, Union

from worksheet_builder.assets import BASE_CSS, KATEX_HEAD
from worksheet_builder.components import render_component
from worksheet_builder.models import (
    QUESTION_MODEL_TYPES,
    AnyBlockModel,
    ComponentModel,
    DocumentBlockModel,
    DocumentLeafModel,
    DocumentModel,
    DocumentRowModel,
    HeadingModel,
    MetaModel,
    PartModel,
    QuestionModel,
    RowModel,
    TaskModel,
    iter_flat_models,
)
from worksheet_builder.questions import RenderMode, render_question
from worksheet_builder.render_helpers import esc
from worksheet_builder.strings import LETTERS, t


def render_header(meta: MetaModel) -> str:
    school = esc(meta.school)
    date = esc(meta.date)
    subject = esc(meta.subject)
    grade = esc(meta.grade)
    title = esc(meta.title)
    parts = ['<div class="sheet-header">']
    parts.append(
        f'<div class="meta-line">{t("school_class")} <span class="blank">{school}</span>'
        f' {t("date")} <span class="blank">{date}</span>'
        f' {t("full_name")} <span class="blank" style="min-width:225px;"></span></div>'
    )
    parts.append(f'<div class="sheet-title">{title}</div>')
    # Подзаголовок собирается только из заполненных частей: пустые
    # subject/grade не оставляют висячих разделителей и суффикса "класс".
    subtitle_bits = []
    if subject:
        subtitle_bits.append(subject)
    if grade:
        subtitle_bits.append(f'{grade} {t("grade_suffix")}')
    if subtitle_bits:
        parts.append(f'<div class="sheet-subtitle">{" &middot; ".join(subtitle_bits)}</div>')
    if meta.instructions:
        parts.append(f'<div class="sheet-instructions">{esc(meta.instructions)}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_task_number_line(index: int, points: float | None) -> str:
    # Номер задания — всегда своя отдельная строка сверху, с баллами задания,
    # если они заданы. Описательный текст задания — не часть этой строки: он
    # живёт как обычный `text`-блок в `blocks` (см. task-schema.md).
    points_html = f' <span class="task-points">({esc(points)} {t("points_suffix")})</span>' if points else ""
    return f'<div class="task-header"><span class="task-num">{index}.</span>{points_html}</div>'


def render_label_line(label: str | None, points: float | None) -> str:
    # Маленькая строка только из буквы подзадания и/или его баллов — без
    # текста (условие подзадания — обычный `text`-блок внутри `part`).
    # Пусто, если ни буквы, ни баллов нет.
    label_html = f'<span class="subtask-label">{esc(label)})</span>' if label else ""
    points_html = f' <span class="task-points">({esc(points)} {t("points_suffix")})</span>' if points else ""
    if not label_html and not points_html:
        return ""
    return f'<div class="task-header">{label_html}{points_html}</div>'


def compute_part_labels(parts: list[PartModel]) -> dict[int, str]:
    """Буква = part, по порядку следования. Явный `label` побеждает;
    авто-буквы пропускают любое значение, уже занятое явным label
    (см. task-schema.md). Чистая функция: ничего не мутирует, возвращает
    {id(part): буква} — рендер один и тот же независимо от того, сколько
    раз задание рендерилось до этого."""
    explicit_labels = {part.label for part in parts if part.label}
    auto_letters = iter(letter for letter in LETTERS if letter not in explicit_labels)
    return {id(part): part.label or next(auto_letters) for part in parts}


def render_leaf(block: Union[ComponentModel, QuestionModel], mode: RenderMode) -> str:
    if isinstance(block, QUESTION_MODEL_TYPES):
        body = render_question(block, mode)
    else:
        body = render_component(block)
    return f'<div class="task-block">{body}</div>'


def render_part(part: PartModel, mode: RenderMode, part_labels: dict[int, str]) -> str:
    header_html = render_label_line(part_labels.get(id(part)), part.points)
    inner = "".join(render_block(block, mode, part_labels) for block in part.blocks)
    return f'<div class="task-part">{header_html}{inner}</div>'


def render_row(row: RowModel, mode: RenderMode, part_labels: dict[int, str]) -> str:
    # Дети всегда делят строку поровну — грид с равными колонками
    # (grid-auto-columns: 1fr в BASE_CSS) сам корректно учитывает gap,
    # никакой инлайновой арифметики ширин здесь нет.
    cols = "".join(
        f'<div class="task-col">{render_block(block, mode, part_labels)}</div>' for block in row.blocks
    )
    return f'<div class="task-row">{cols}</div>'


def render_block(block: AnyBlockModel, mode: RenderMode, part_labels: dict[int, str]) -> str:
    if isinstance(block, RowModel):
        return render_row(block, mode, part_labels)
    if isinstance(block, PartModel):
        return render_part(block, mode, part_labels)
    return render_leaf(block, mode)


def render_task(index: int, task: TaskModel, is_teacher: bool) -> str:
    mode: RenderMode = "teacher" if is_teacher else "student"

    # Буквы — по сплющенному обходу: part внутри row получает букву так же,
    # как получал бы, стоя на уровне задания (row прозрачен, см. models.py).
    part_labels = compute_part_labels(
        [b for b in iter_flat_models(task.blocks) if isinstance(b, PartModel)]
    )

    # Номер задания — всегда своя отдельная строка сверху (см.
    # render_task_number_line).
    block_htmls = [render_task_number_line(index, task.points)]
    for block in task.blocks:
        block_htmls.append(render_block(block, mode, part_labels))

    return f'<div class="task"><div class="task-blocks">{"".join(block_htmls)}</div></div>'


# --- Режим «документ» (--document): произвольный текст + визуалы ---

def _render_document_leaf(block: DocumentLeafModel) -> str:
    if isinstance(block, HeadingModel):
        return f'<div class="doc-heading">{esc(block.text)}</div>'
    return f'<div class="task-block">{render_component(block)}</div>'


def _render_document_block(block: DocumentBlockModel) -> str:
    if isinstance(block, DocumentRowModel):
        cols = "".join(
            f'<div class="task-col">{_render_document_leaf(b)}</div>' for b in block.blocks
        )
        return f'<div class="task-row">{cols}</div>'
    return _render_document_leaf(block)


def build_plain_document(doc: DocumentModel, source: dict[str, Any] | None = None) -> str:
    """HTML документа (конспект/теория/текст с иллюстрациями): та же оболочка,
    что у листа (колонка 800px, BASE_CSS, KaTeX), но без анкеты-шапки,
    нумерации заданий и режимов student/teacher — документ один. `source` —
    сырой авторский JSON для встраивания: как у тичер-варианта листа, одного
    HTML достаточно, чтобы продолжить правки в новой сессии."""
    header = (
        f'<div class="sheet-header"><div class="sheet-title">{esc(doc.title)}</div></div>'
        if doc.title else ""
    )
    body = header + "".join(_render_document_block(b) for b in doc.blocks)
    source_html = f"\n{render_source_script(source)}" if source is not None else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{esc(doc.title or t("default_document_title"))}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{body}{source_html}
</body>
</html>"""


def render_source_script(source: dict[str, Any]) -> str:
    """Черновик (сырые авторские meta + tasks), встроенный в HTML: файл
    учителя и есть черновик — в новой сессии его достаточно загрузить
    обратно. `<` экранируется как `\\u003c` (валидный JSON-эскейп), чтобы
    никакой авторский текст не мог закрыть тег `</script>` досрочно."""
    payload = json.dumps(source, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id="worksheet-source">{payload}</script>'


def build_document(
    meta: MetaModel,
    tasks: list[TaskModel],
    is_teacher: bool,
    source: dict[str, Any] | None = None,
) -> str:
    """`tasks` — уже распарсенные модели (см. cli.parse_tasks): парсинг и
    валидация происходят один раз, а не на каждый вариант листа. `source` —
    сырой черновик для встраивания в документ; передаётся только для
    тичер-варианта (в нём и так есть все ответы) полного листа, превью
    отдельных заданий живут без него."""
    body = [render_header(meta)]
    for i, task in enumerate(tasks, start=1):
        body.append(render_task(i, task, is_teacher))
    variant = t("teacher_variant") if is_teacher else t("student_variant")
    source_html = f"\n{render_source_script(source)}" if source is not None else ""
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{esc(meta.title or t("default_title"))} — {variant}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{''.join(body)}{source_html}
</body>
</html>"""
