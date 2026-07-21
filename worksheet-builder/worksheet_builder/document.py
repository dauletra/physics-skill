"""Собирает HTML документа из моделей (models.py): `DocumentModel`
(манифест) + список верхнеуровневых блоков. Контейнеры (`task`/`part`/`row`)
рендерятся здесь; листья уходят в render_component/render_question; ответы
заданий собираются в секцию «Ответы» в конце документа
(`build_answers_section`)."""

import json
from typing import Any, Union

from worksheet_builder.assets import BASE_CSS, KATEX_HEAD
from worksheet_builder.components import render_component
from worksheet_builder.models import (
    QUESTION_MODEL_TYPES,
    AnyBlockModel,
    ComponentModel,
    DocBlockModel,
    DocRowModel,
    DocumentModel,
    HeadingModel,
    PartModel,
    QuestionModel,
    RowModel,
    TaskModel,
    iter_flat_models,
)
from worksheet_builder.questions import render_answer, render_question
from worksheet_builder.render_helpers import esc
from worksheet_builder.strings import LETTERS, t


def render_header(doc: DocumentModel) -> str:
    """Шапка документа: заголовок всегда (если задан); анкета-строка,
    подзаголовок и инструкция — только при наличии `header` в манифесте
    (конспекту анкета не нужна, самостоятельной работе — нужна)."""
    header = doc.header
    if not doc.title and header is None:
        return ""
    parts = ['<div class="sheet-header">']
    if header is not None:
        school = esc(header.school)
        date = esc(header.date)
        parts.append(
            f'<div class="meta-line">{t("school_class")} <span class="blank">{school}</span>'
            f' {t("date")} <span class="blank">{date}</span>'
            f' {t("full_name")} <span class="blank" style="min-width:225px;"></span></div>'
        )
    if doc.title:
        parts.append(f'<div class="sheet-title">{esc(doc.title)}</div>')
    if header is not None:
        # Подзаголовок собирается только из заполненных частей: пустые
        # subject/grade не оставляют висячих разделителей и суффикса "класс".
        subtitle_bits = []
        if header.subject:
            subtitle_bits.append(esc(header.subject))
        if header.grade:
            subtitle_bits.append(f'{esc(header.grade)} {t("grade_suffix")}')
        if subtitle_bits:
            parts.append(f'<div class="sheet-subtitle">{" &middot; ".join(subtitle_bits)}</div>')
        if header.instructions:
            parts.append(f'<div class="sheet-instructions">{esc(header.instructions)}</div>')
    parts.append("</div>")
    return "".join(parts)


def render_task_number_line(index: int, points: float | None) -> str:
    # Номер задания — всегда своя отдельная строка сверху, с баллами задания,
    # если они заданы. Описательный текст задания — не часть этой строки: он
    # живёт как обычный `text`-блок в `blocks` (см. document-schema.md).
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
    (см. document-schema.md). Чистая функция: ничего не мутирует, возвращает
    {id(part): буква} — рендер один и тот же независимо от того, сколько
    раз задание рендерилось до этого."""
    explicit_labels = {part.label for part in parts if part.label}
    auto_letters = iter(letter for letter in LETTERS if letter not in explicit_labels)
    return {id(part): part.label or next(auto_letters) for part in parts}


def render_leaf(block: Union[ComponentModel, QuestionModel]) -> str:
    if isinstance(block, QUESTION_MODEL_TYPES):
        body = render_question(block)
    else:
        body = render_component(block)
    return f'<div class="task-block">{body}</div>'


def render_part(part: PartModel, part_labels: dict[int, str]) -> str:
    header_html = render_label_line(part_labels.get(id(part)), part.points)
    inner = "".join(render_task_block(block, part_labels) for block in part.blocks)
    return f'<div class="task-part">{header_html}{inner}</div>'


def render_row(row: RowModel, part_labels: dict[int, str]) -> str:
    # Дети всегда делят строку поровну — грид с равными колонками
    # (grid-auto-columns: 1fr в BASE_CSS) сам корректно учитывает gap,
    # никакой инлайновой арифметики ширин здесь нет.
    cols = "".join(
        f'<div class="task-col">{render_task_block(block, part_labels)}</div>' for block in row.blocks
    )
    return f'<div class="task-row">{cols}</div>'


def render_task_block(block: AnyBlockModel, part_labels: dict[int, str]) -> str:
    if isinstance(block, RowModel):
        return render_row(block, part_labels)
    if isinstance(block, PartModel):
        return render_part(block, part_labels)
    return render_leaf(block)


def _task_part_labels(task: TaskModel) -> dict[int, str]:
    # Буквы — по сплющенному обходу: part внутри row получает букву так же,
    # как получал бы, стоя на уровне задания (row прозрачен, см. models.py).
    return compute_part_labels(
        [b for b in iter_flat_models(task.blocks) if isinstance(b, PartModel)]
    )


def render_task(index: int, task: TaskModel) -> str:
    """Тело задания под номером `index` — без ответов: они собираются отдельно
    в секцию «Ответы» (build_answers_section) под тем же номером."""
    part_labels = _task_part_labels(task)

    # Номер задания — всегда своя отдельная строка сверху (см.
    # render_task_number_line).
    block_htmls = [render_task_number_line(index, task.points)]
    for block in task.blocks:
        block_htmls.append(render_task_block(block, part_labels))

    return f'<div class="task"><div class="task-blocks">{"".join(block_htmls)}</div></div>'


def render_doc_block(block: DocBlockModel, index: int | None = None) -> str:
    """Один верхнеуровневый блок документа; `index` — номер задания, если
    блок — task (нумерация сквозная по документу, см. build_document)."""
    if isinstance(block, TaskModel):
        assert index is not None
        return render_task(index, block)
    if isinstance(block, HeadingModel):
        return f'<div class="doc-heading">{esc(block.text)}</div>'
    if isinstance(block, DocRowModel):
        cols = "".join(
            f'<div class="task-col">{render_doc_block(b)}</div>' for b in block.blocks
        )
        return f'<div class="task-row">{cols}</div>'
    return f'<div class="task-block">{render_component(block)}</div>'


def iter_task_answers(task: TaskModel) -> "list[tuple[str, QuestionModel]]":
    """Пары (буква-или-пустая-строка, вопрос) задания в порядке следования:
    одиночный вопрос — без буквы, вопросы в part — с буквой part."""
    part_labels = _task_part_labels(task)
    pairs: list[tuple[str, QuestionModel]] = []
    for block in iter_flat_models(task.blocks):
        if isinstance(block, QUESTION_MODEL_TYPES):
            pairs.append(("", block))
        elif isinstance(block, PartModel):
            for inner in iter_flat_models(block.blocks):
                if isinstance(inner, QUESTION_MODEL_TYPES):
                    pairs.append((part_labels[id(block)], inner))
    return pairs


def build_answers_section(numbered_tasks: list[tuple[int, TaskModel]]) -> str:
    """Секция «Ответы» в конце документа: по строке на вопрос с ответом или
    пояснением («3.» у одиночного вопроса, «3. б)» у подзадания). Задания
    без единого ответа/пояснения пропускаются; пустая секция не печатается
    вовсе — у чистого конспекта её нет."""
    items = []
    for index, task in numbered_tasks:
        for label, question in iter_task_answers(task):
            answer_html = render_answer(question)
            if not answer_html and not question.explanation:
                continue
            num = f"{index}." + (f" {esc(label)})" if label else "")
            body = answer_html
            if question.explanation:
                body += (
                    f'<div class="answers-explanation">'
                    f'<strong>{t("explanation_label")}</strong> {esc(question.explanation)}</div>'
                )
            items.append(
                f'<div class="answers-item"><span class="answers-num">{num}</span>'
                f'<div class="answers-body">{body}</div></div>'
            )
    if not items:
        return ""
    return (
        '<div class="answers-section">'
        f'<div class="answers-title">{t("answers_title")}</div>'
        f'{"".join(items)}</div>'
    )


def render_source_script(source: dict[str, Any]) -> str:
    """Черновик (сырые авторские document.json + блоки), встроенный в HTML:
    итоговый файл и есть черновик — в новой сессии его достаточно загрузить
    обратно. `<` экранируется как `\\u003c` (валидный JSON-эскейп), чтобы
    никакой авторский текст не мог закрыть тег `</script>` досрочно."""
    payload = json.dumps(source, ensure_ascii=False).replace("<", "\\u003c")
    return f'<script type="application/json" id="document-source">{payload}</script>'


def _numbered(blocks: list[DocBlockModel]) -> list[tuple[DocBlockModel, int | None]]:
    """Сквозная нумерация: task-блоки получают 1..N по порядку появления,
    остальные блоки номера не сдвигают."""
    result: list[tuple[DocBlockModel, int | None]] = []
    counter = 0
    for block in blocks:
        if isinstance(block, TaskModel):
            counter += 1
            result.append((block, counter))
        else:
            result.append((block, None))
    return result


def _wrap_html(title: str, body: str, source_html: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>{esc(title or t("default_title"))}</title>
{KATEX_HEAD}
<style>{BASE_CSS}</style>
</head>
<body>
{body}{source_html}
</body>
</html>"""


def build_document(
    doc: DocumentModel,
    blocks: list[DocBlockModel],
    with_answers: bool = True,
    source: dict[str, Any] | None = None,
) -> str:
    """Единственный HTML-собиратель: конспект, объяснение, задания и любые
    их комбинации. `blocks` — уже распарсенные модели (см. cli.parse_blocks):
    парсинг и валидация происходят один раз. `with_answers` управляет только
    секцией «Ответы» в конце — тела заданий ответов не содержат. `source` —
    сырой черновик для встраивания; передаётся только в полный вариант
    (в варианте без ответов черновик раскрыл бы ответы через исходный код)."""
    numbered = _numbered(blocks)
    body = [render_header(doc)]
    for block, index in numbered:
        body.append(render_doc_block(block, index))
    if with_answers:
        body.append(build_answers_section(
            [(index, block) for block, index in numbered
             if isinstance(block, TaskModel) and index is not None]
        ))
    source_html = f"\n{render_source_script(source)}" if source is not None else ""
    return _wrap_html(doc.title, "".join(body), source_html)


def build_preview(doc: DocumentModel, blocks: list[DocBlockModel], block_id: str) -> str:
    """Превью одного верхнеуровневого блока (`--block`) в реальных стилях:
    задание печатается под своим настоящим сквозным номером и со своей
    строкой ответов; черновик в превью не встраивается — это черновой
    артефакт, а не файл для продолжения сессии."""
    numbered = _numbered(blocks)
    match = next(
        ((block, index) for block, index in numbered
         if getattr(block, "id", None) == block_id),
        None,
    )
    if match is None:
        raise KeyError(block_id)
    block, index = match
    body = render_doc_block(block, index)
    if isinstance(block, TaskModel) and index is not None:
        body += build_answers_section([(index, block)])
    return _wrap_html(doc.title, body)
