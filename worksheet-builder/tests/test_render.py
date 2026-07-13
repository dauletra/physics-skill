"""Golden-тесты рендера: каждый вид вопроса в обоих режимах + полный пример.

Сравнение — с эталонными файлами в tests/golden/ (пересъём: REGEN_GOLDEN=1).
Точка входа — стабильный шов parse_task + render_task/build_document,
чтобы тесты переживали внутренние перестройки парсинга."""
from pathlib import Path

import pytest
from conftest import MINIMAL_TASKS

from worksheet_builder.cli import load_workspace
from worksheet_builder.document import build_document, render_task
from worksheet_builder.models import parse_task

EXAMPLE_DIR = Path(__file__).parent.parent / "examples" / "kinematics-9th-grade"


def load_example_tasks():
    meta, raw_tasks = load_workspace(EXAMPLE_DIR)
    return meta, [parse_task(raw) for raw in raw_tasks]


@pytest.mark.parametrize("kind", sorted(MINIMAL_TASKS))
@pytest.mark.parametrize("mode", ["student", "teacher"])
def test_task_golden(kind, mode, golden):
    task = parse_task(MINIMAL_TASKS[kind])
    html = render_task(1, task, is_teacher=(mode == "teacher"))
    golden(f"{kind}_{mode}", html)


@pytest.mark.parametrize("mode", ["student", "teacher"])
def test_example_workspace_golden(mode, golden):
    meta, tasks = load_example_tasks()
    html = build_document(meta, tasks, is_teacher=(mode == "teacher"))
    golden(f"example_{mode}", html)


def test_student_hides_answers():
    """Смоук поверх голденов: в студенческой версии нет ни одного
    тичер-артефакта (рамок ответа, отмеченных вариантов, значений blanks)."""
    meta, tasks = load_example_tasks()
    html = build_document(meta, tasks, is_teacher=False)
    # Ищем классы в разметке (в <style> те же имена присутствуют легитимно).
    assert 'class="answer-block"' not in html
    assert 'class="mc-correct"' not in html
    assert 'class="fill-blank answered"' not in html


def test_choice_multiple_prints_hint():
    """При select: multiple ученик обязан видеть, что верных ответов больше
    одного — single и multiple рендерятся одинаковым списком."""
    def choice_task(select, correct_flags):
        return parse_task({"id": "t-c", "blocks": [{
            "type": "choice", "select": select,
            "options": [{"text": f"вариант {i}", "correct": flag}
                        for i, flag in enumerate(correct_flags)],
        }]})

    multiple = render_task(1, choice_task("multiple", [True, True, False]), is_teacher=False)
    assert 'class="choice-hint"' in multiple
    single = render_task(1, choice_task("single", [True, False, False]), is_teacher=False)
    assert 'class="choice-hint"' not in single


def test_header_omits_empty_subtitle_parts():
    """Пустые subject/grade не оставляют висячих "·" и суффикса "класс"."""
    from worksheet_builder.document import render_header
    from worksheet_builder.models import parse_meta

    header = render_header(parse_meta({"title": "Лист"}))
    assert "sheet-subtitle" not in header
    # Смотрим содержимое именно подзаголовка: слово "класс" в шапке есть
    # легитимно ("Школа/класс:"), а "·" не должен висеть без пары.
    only_subject = render_header(parse_meta({"title": "Лист", "subject": "Физика"}))
    assert '<div class="sheet-subtitle">Физика</div>' in only_subject
    only_grade = render_header(parse_meta({"title": "Лист", "grade": "9"}))
    assert '<div class="sheet-subtitle">9 класс</div>' in only_grade
    both = render_header(parse_meta({"title": "Лист", "subject": "Физика", "grade": "9"}))
    assert '<div class="sheet-subtitle">Физика &middot; 9 класс</div>' in both
