"""Golden-тесты рендера: каждый вид вопроса (тело задания + его строки в
секции «Ответы») + полный пример-документ.

Сравнение — с эталонными файлами в tests/golden/ (пересъём: REGEN_GOLDEN=1).
Точка входа — стабильный шов parse_block + render_task/build_document,
чтобы тесты переживали внутренние перестройки парсинга."""
from pathlib import Path

import pytest

from conftest import MINIMAL_TASKS
from worksheet_builder.cli import load_workspace, parse_blocks
from worksheet_builder.document import (
    build_answers_section,
    build_document,
    render_header,
    render_task,
)
from worksheet_builder.models import TaskModel, parse_block, parse_document

EXAMPLE_DIR = (
    Path(__file__).parent.parent / "worksheet-builder" / "examples" / "kinematics-9th-grade"
)


def load_example():
    doc, _raw_doc, raw_blocks = load_workspace(EXAMPLE_DIR)
    return doc, parse_blocks(raw_blocks)


def render_task_with_answers(raw_task: dict) -> str:
    """Тело задания + его строки в секции ответов — ровно то, что попадает в
    документ от одного задания (без оболочки страницы)."""
    task = parse_block(raw_task)
    assert isinstance(task, TaskModel)
    return render_task(1, task) + build_answers_section([(1, task)])


@pytest.mark.parametrize("kind", sorted(MINIMAL_TASKS))
def test_task_golden(kind, golden):
    golden(kind, render_task_with_answers(MINIMAL_TASKS[kind]))


def test_example_workspace_golden(golden):
    doc, blocks = load_example()
    golden("example", build_document(doc, blocks, with_answers=True))


def test_no_answers_variant_hides_answers():
    """Раздаточный вариант: ни секции ответов, ни встроенного черновика —
    и никаких ответов в телах заданий (их там нет по построению)."""
    doc, blocks = load_example()
    html = build_document(doc, blocks, with_answers=False)
    assert 'class="answers-section"' not in html
    assert 'id="document-source"' not in html


def test_answers_section_lists_every_numbered_task():
    """У примера каждое задание с ответом или пояснением получает строку в
    секции ответов под своим сквозным номером."""
    doc, blocks = load_example()
    html = build_document(doc, blocks, with_answers=True)
    n_tasks = sum(1 for b in blocks if isinstance(b, TaskModel))
    assert n_tasks >= 15
    # Первый и последний номера присутствуют в секции ответов.
    answers = html.split('class="answers-section"', 1)[1]
    assert '<span class="answers-num">1.' in answers
    assert f'<span class="answers-num">{n_tasks}.' in answers


def test_choice_multiple_prints_hint():
    """При select: multiple решающий обязан видеть, что верных ответов больше
    одного — single и multiple рендерятся одинаковым списком."""
    def choice_task(select, correct_flags):
        return {"type": "task", "id": "t-c", "blocks": [
            {"type": "text", "body": "Выберите верное."},
            {"type": "choice", "select": select,
             "options": [{"text": f"вариант {i}", "correct": flag}
                         for i, flag in enumerate(correct_flags)]},
        ]}

    multiple = render_task_with_answers(choice_task("multiple", [True, True, False]))
    assert 'class="choice-hint"' in multiple
    single = render_task_with_answers(choice_task("single", [True, False, False]))
    assert 'class="choice-hint"' not in single


def test_header_omits_empty_subtitle_parts():
    """Пустые subject/grade не оставляют висячих "·" и суффикса "класс";
    без `header` в манифесте нет ни анкеты-строки, ни подзаголовка."""
    no_header = render_header(parse_document({"title": "Конспект"}))
    assert "meta-line" not in no_header and "sheet-subtitle" not in no_header
    assert '<div class="sheet-title">Конспект</div>' in no_header

    bare = render_header(parse_document({"title": "Лист", "header": {}}))
    assert "meta-line" in bare and "sheet-subtitle" not in bare
    only_subject = render_header(parse_document(
        {"title": "Лист", "header": {"subject": "Физика"}}))
    assert '<div class="sheet-subtitle">Физика</div>' in only_subject
    only_grade = render_header(parse_document({"title": "Лист", "header": {"grade": "9"}}))
    assert '<div class="sheet-subtitle">9 класс</div>' in only_grade
    both = render_header(parse_document(
        {"title": "Лист", "header": {"subject": "Физика", "grade": "9"}}))
    assert '<div class="sheet-subtitle">Физика &middot; 9 класс</div>' in both


def test_empty_manifest_renders_no_header():
    assert render_header(parse_document({})) == ""
