"""Фузз эскейпинга: в каждое свободнотекстовое поле каждого вида задания
подсовывается HTML-сентинел, и рендер (тело задания + его строки в секции
«Ответы») обязан выдать его экранированным. Это поведенческое принуждение
правила «модель хранит сырой текст — эскейпит рендер»: забытый `esc()` в
новом виде вопроса валит этот тест, а не доживает до готового документа.
Новый вид покрывается автоматически, как только его минимальное задание
добавлено в MINIMAL_TASKS."""
import pytest

from conftest import MINIMAL_TASKS
from worksheet_builder.document import build_answers_section, render_task
from worksheet_builder.models import TaskModel, parse_block

SENTINEL = '<img src=x>&"'
ESCAPED = "&lt;img src=x&gt;&amp;&quot;"

# Ключи, чьи значения — не свободный текст, а закрытые словари/ссылки/буквы:
# их порча ломала бы валидацию, а не проверяла эскейпинг.
STRUCTURAL_KEYS = {"type", "id", "marker", "columns", "style", "chart_type",
                   "select", "match", "label", "kind", "ruling"}


def poison(node, parent_type=None, structural=STRUCTURAL_KEYS):
    """Дописывает SENTINEL в каждое строковое значение, кроме структурных
    ключей. `categories`/`category` портятся одинаково (одна функция), так
    что ссылка категория→список остаётся валидной; в `template` сентинел
    дописывается в конец — плейсхолдеры не задеваются. `structural`
    переопределяется, когда набор структурных ключей другой (например,
    standalone-визуалы: там `label` — свободный текст серии, а не буква
    part — см. test_standalone.py)."""
    if isinstance(node, dict):
        block_type = node.get("type", parent_type)
        return {
            key: (value if key in structural else poison(value, block_type, structural))
            for key, value in node.items()
        }
    if isinstance(node, list):
        return [poison(item, parent_type, structural) for item in node]
    if isinstance(node, str):
        return node + SENTINEL
    return node


@pytest.mark.parametrize("kind", sorted(MINIMAL_TASKS))
def test_authored_text_is_escaped(kind):
    task = parse_block(poison(MINIMAL_TASKS[kind]))
    assert isinstance(task, TaskModel)
    html = render_task(1, task) + build_answers_section([(1, task)])
    assert SENTINEL not in html, f"сырой HTML из данных просочился в рендер ({kind})"
    assert ESCAPED in html, f"сентинел вообще не попал в вывод ({kind})"


def test_sup_sub_still_pass_through():
    """Контр-проверка: легитимные <sup>/<sub> (symbols.md) esc() пропускает."""
    task = parse_block({"type": "task", "id": "t-sup", "blocks": [
        {"type": "text", "body": "м/с<sup>2</sup> и x<sub>max</sub>"},
        {"type": "open"},
    ]})
    assert isinstance(task, TaskModel)
    html = render_task(1, task)
    assert "<sup>2</sup>" in html and "<sub>max</sub>" in html
