"""Свойства рендера, а не валидация контента: адресат этих тестов —
разработчик пакета, а не автор JSON. Ловят класс ошибок, при котором
валидный черновик даёт документ, противоречащий сам себе: задание
печатается пустым, а строка в секции «Ответы» на него всё равно ссылается
(так вышло, когда `open` перестал печатать линии под ответ).

Покрытие расширяется само: новый вид вопроса попадает сюда, как только его
минимальное задание добавлено в MINIMAL_TASKS (conftest.py)."""
import re

import pytest

from conftest import MINIMAL_TASKS
from worksheet_builder.document import build_answers_section, render_task
from worksheet_builder.models import TaskModel, parse_block

TAG_RE = re.compile(r"<[^>]+>")


def visible_text(html: str) -> str:
    """Видимый текст: разметка снята, текст внутри SVG (подписи осей, штрихи,
    caption) сохраняется — он на листе виден так же, как абзац."""
    return TAG_RE.sub(" ", html).strip()


def render(kind: str) -> tuple[str, str]:
    task = parse_block(MINIMAL_TASKS[kind])
    assert isinstance(task, TaskModel)
    return render_task(1, task), build_answers_section([(1, task)])


@pytest.mark.parametrize("kind", sorted(MINIMAL_TASKS))
def test_minimal_task_renders_visible_content(kind):
    """Минимальная валидная форма задания не печатает пустоту."""
    body, _ = render(kind)
    assert 'class="task-block"' in body or 'class="task-part"' in body, (
        f"{kind}: ни один дочерний блок не отрендерился — от задания остался номер"
    )
    assert visible_text(body).replace("1.", "").strip(), (
        f"{kind}: в теле нет видимого текста, кроме номера задания"
    )


@pytest.mark.parametrize("kind", sorted(MINIMAL_TASKS))
def test_answers_row_implies_visible_body(kind):
    """Строка в «Ответах» не бывает у задания с пустым телом: иначе документ
    утверждает, что вопрос был, а на листе его нет."""
    body, answers = render(kind)
    if not answers:
        return
    assert visible_text(body).replace("1.", "").strip(), (
        f"{kind}: ответ есть, тело задания пустое"
    )
