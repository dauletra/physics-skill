"""Негативная таблица: битый JSON блока-задания → ValueError с внятным
сообщением и путём до блока, поднятая при загрузке (не traceback и не
молчаливый фолбэк). Вся валидация — pydantic-модели в models.py."""
import pytest

from worksheet_builder.models import parse_block


def load_error(task_dict) -> str:
    with pytest.raises(ValueError) as excinfo:
        parse_block(task_dict)
    return str(excinfo.value)


def make_task(*blocks, **extra):
    return {"type": "task", "id": "t-bad", "blocks": list(blocks), **extra}


# --- Инварианты состава и payload-инварианты видов ---

def test_unknown_block_type():
    msg = load_error(make_task({"type": "picture"}))
    assert "unknown block type" in msg and "blocks[0]" in msg


def test_part_and_bare_question_siblings():
    msg = load_error(make_task(
        {"type": "part", "blocks": [{"type": "open"}]},
        {"type": "open"},
    ))
    assert "cannot be siblings" in msg


def test_two_bare_questions():
    msg = load_error(make_task({"type": "open"}, {"type": "open"}))
    assert "more than one bare question" in msg


def test_nested_row_rejected():
    msg = load_error(make_task(
        {"type": "row", "blocks": [{"type": "row", "blocks": [{"type": "text", "body": "x"}]}]}
    ))
    assert "nested rows" in msg


def test_nested_part_rejected():
    msg = load_error(make_task(
        {"type": "part", "blocks": [{"type": "part", "blocks": [{"type": "open"}]}]}
    ))
    assert "nested parts" in msg


def test_part_needs_exactly_one_question():
    msg = load_error(make_task({"type": "part", "blocks": [{"type": "text", "body": "x"}]}))
    assert "exactly one question" in msg


def test_width_rejected():
    msg = load_error(make_task(
        {"type": "row", "blocks": [
            {"type": "text", "body": "x", "width": 50},
            {"type": "text", "body": "y"},
        ]}
    ))
    assert "width" in msg


def test_choice_single_needs_one_correct():
    msg = load_error(make_task({"type": "choice", "select": "single", "options": [
        {"text": "а", "correct": True}, {"text": "б", "correct": True},
    ]}))
    assert "exactly one correct" in msg


def test_rank_positions_permutation():
    msg = load_error(make_task({"type": "rank", "items": [
        {"text": "а", "position": 1}, {"text": "б", "position": 3},
    ]}))
    assert "permutation" in msg


def test_match_dangling_ref():
    msg = load_error(make_task({"type": "match",
                                "left": [{"text": "а", "match": "nope"}],
                                "right": [{"id": "m", "text": "м"}]}))
    assert "not found" in msg


def test_fill_text_placeholder_mismatch():
    msg = load_error(make_task({"type": "fill_text",
                                "template": "Сила — ___u___.",
                                "blanks": {"u": "Н", "extra": "Дж"}}))
    assert "placeholder" in msg.lower() or "blanks" in msg


def test_open_response_is_gone():
    # Место под ответ переехало в соседний компонент `paper`/`answer_line`
    # (раскладка не живёт в payload вопроса) — старое поле теперь опечатка.
    msg = load_error(make_task({"type": "open", "response": "lines:4"}))
    assert "response" in msg


def test_bar_multiple_series():
    msg = load_error(make_task({"type": "graph", "chart_type": "bar",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [0, 5],
                                "series": [{"points": [[1, 1]]}, {"points": [[2, 2]]}]}))
    assert "single series" in msg


def test_unknown_chart_grid():
    msg = load_error(make_task({"type": "graph", "grid": "millimeter",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [0, 5]}))
    assert "grid" in msg


def test_unknown_chart_type():
    msg = load_error(make_task({"type": "graph", "chart_type": "pie",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [0, 5]}))
    assert "chart_type" in msg


def _instrument(**overrides):
    base = {"type": "instrument", "kind": "ammeter", "unit": "А",
            "min": 0, "max": 3, "step": 0.1, "value": 1.35}
    base.update(overrides)
    return base


def test_instrument_unknown_kind():
    msg = load_error(make_task(_instrument(kind="barometer2000")))
    assert "kind" in msg


def test_instrument_degenerate_range():
    msg = load_error(make_task(_instrument(min=3, max=3)))
    assert "min < max" in msg


def test_instrument_step_must_divide_range():
    msg = load_error(make_task(_instrument(step=0.7)))
    assert "divide" in msg


def test_instrument_too_many_divisions():
    # 300 делений на дуге циферблата нечитаемы; лимит зависит от семейства.
    msg = load_error(make_task(_instrument(step=0.01)))
    assert "divisions" in msg
    # Та же плотность у линейки легальна (лимит семейства strip выше).
    parse_block(make_task(_instrument(kind="ruler", unit="см", max=10, step=0.1)))


def test_instrument_value_outside_scale():
    msg = load_error(make_task(_instrument(value=3.5)))
    assert "outside the scale" in msg


def test_instrument_value_between_marks_is_legal():
    # Показание между штрихами — суть задач на погрешность, не ошибка.
    parse_block(make_task(_instrument(value=1.234)))


def test_instrument_empty_scale_is_legal():
    parse_block(make_task(_instrument(value=None)))


def test_label_step_must_be_multiple_of_step():
    # 0.25 при цене деления 0.1 — подписи не попадали бы на штрихи.
    msg = load_error(make_task(_instrument(label_step=0.25)))
    assert "label_step" in msg and "multiple" in msg


def test_label_step_over_label_limit_is_rejected():
    # 31 подпись на дуге (лимит 8): явный label_step не прореживается
    # молча — раз автор сказал явно, рендерер не вправе «поправить».
    msg = load_error(make_task(_instrument(label_step=0.1)))
    assert "label_step" in msg and "limit" in msg
    # Тот же шаг подписей с разумной частотой легален.
    parse_block(make_task(_instrument(label_step=0.5)))


def test_label_step_only_on_tick_scales():
    # У весов и цифрового табло штрихов нет — подписывать нечего.
    msg = load_error(make_task(_instrument(kind="multimeter", unit="В",
                                           max=20, step=0.01, value=12.47,
                                           label_step=5)))
    assert "label_step" in msg and "tick scale" in msg


# --- Бумага (компонент `paper`) ---


def test_paper_square_ruling_needs_cols():
    # Клетку нельзя растянуть по ширине колонки — она перестанет быть
    # квадратной, поэтому ширина обязана быть в данных.
    msg = load_error(make_task({"type": "paper", "ruling": "mm", "rows": 12}))
    assert "cols" in msg
    # Линиям ширина не нужна: без cols поле занимает колонку целиком.
    parse_block(make_task({"type": "paper", "ruling": "lines", "rows": 4}))


def test_paper_too_wide_for_column():
    msg = load_error(make_task({"type": "paper", "ruling": "mm", "rows": 4, "cols": 40}))
    assert "cols" in msg and "column" in msg


def test_paper_too_tall():
    msg = load_error(make_task({"type": "paper", "ruling": "mm", "rows": 200, "cols": 10}))
    assert "rows" in msg
    # Ровно та же ошибка ловит перепутанную единицу: 120 «клеток» вместо
    # 12 см — типовая опечатка автора миллиметровки.
    assert "at most" in msg


def test_paper_unknown_ruling():
    msg = load_error(make_task({"type": "paper", "ruling": "hexagons", "rows": 4}))
    assert "ruling" in msg


def test_paper_zero_rows():
    msg = load_error(make_task({"type": "paper", "ruling": "lines", "rows": 0}))
    assert "rows" in msg


# --- Метрология: класс точности и многопредельность ---


def test_accuracy_class_only_on_dials():
    msg = load_error(make_task(_instrument(kind="ruler", unit="см",
                                           max=10, value=None, accuracy_class=0.5)))
    assert "dial" in msg


def test_accuracy_class_closed_set():
    # 0.3 — не класс точности по ГОСТ 8.401; произвольное число — ошибка.
    msg = load_error(make_task(_instrument(accuracy_class=0.3)))
    assert "accuracy_class" in msg
    parse_block(make_task(_instrument(accuracy_class=1)))  # 1 == 1.0 легален


def test_ranges_only_on_electric():
    msg = load_error(make_task(_instrument(kind="manometer", unit="кПа",
                                           ranges=[100, 400])))
    assert "ammeter/voltmeter" in msg


def test_ranges_must_increase():
    msg = load_error(make_task(_instrument(max=5, ranges=[5, 1])))
    assert "increasing" in msg


def test_exactly_two_ranges():
    # Двойная шкала — ровно два предела; три ряда чисел на дуге нечитаемы.
    msg = load_error(make_task(_instrument(max=5, ranges=[0.2, 1, 5])))
    assert "2" in msg


def test_dual_scale_must_start_at_zero_or_below():
    msg = load_error(make_task(_instrument(min=1, max=3, ranges=[0.6, 3], value=None)))
    assert "start at 0" in msg
    # Заход в минус легален (−1…3 А, как у J0407), показание может быть
    # отрицательным (стрелка левее нуля при обратной полярности).
    parse_block(make_task(_instrument(min=-1, max=3, ranges=[0.6, 3], value=-0.4)))


def test_dual_scale_max_is_larger_range():
    msg = load_error(make_task(_instrument(max=3, ranges=[0.6, 6])))
    assert "larger range" in msg


def test_dual_scale_must_be_round():
    # Пары 3/0.7: внутренняя цена деления 0.1 x 0.7/3 - некруглая.
    msg = load_error(make_task(_instrument(max=3, ranges=[0.7, 3])))
    assert "non-round" in msg
    # Реальные школьные пары легальны: 3/0.6 А и 6/3 В.
    parse_block(make_task(_instrument(max=3, ranges=[0.6, 3])))
    parse_block(make_task(_instrument(kind="voltmeter", unit="В",
                                     max=6, step=0.2, ranges=[3, 6], value=2.5)))


def test_selected_range_is_gone():
    # Поле убрано при переходе на двойную шкалу — теперь это опечатка.
    msg = load_error(make_task(_instrument(max=3, ranges=[0.6, 3], selected_range=3)))
    assert "selected_range" in msg


def test_digital_value_must_match_discreteness():
    # У табло нет «между штрихами»: показание кратно дискретности.
    msg = load_error(make_task(_instrument(kind="multimeter", unit="В",
                                           max=20, step=0.01, value=12.472)))
    assert "multiple of step" in msg


def test_digital_dense_scale_is_legal():
    # 2000 «делений» дискретности — норма для табло (лимит штрихов не про него).
    parse_block(make_task(_instrument(kind="multimeter", unit="В",
                                     max=20, step=0.01, value=12.47)))


def test_vernier_only_on_caliper():
    msg = load_error(make_task(_instrument(vernier=10)))
    assert "caliper" in msg


def test_caliper_value_must_match_precision():
    # 27.43 не кратно точности нониуса 0.1 — совпадающий штрих не определён.
    msg = load_error(make_task(_instrument(kind="caliper", unit="мм",
                                           max=40, step=1, vernier=10, value=27.43)))
    assert "precision" in msg


def test_caliper_vernier_must_fit_on_bar():
    # Нониус длиной 9 мм не помещается правее value = 35 на шкале 0-40.
    msg = load_error(make_task(_instrument(kind="caliper", unit="мм",
                                           max=40, step=1, vernier=10, value=35)))
    assert "fit" in msg


# --- Рычажные весы ---


def _balance(**overrides):
    base = _instrument(kind="balance", unit="г", min=0, max=200, step=1,
                       value=75, weights=[50, 20, 5])
    base.update(overrides)
    return base


def test_weights_only_on_balance():
    msg = load_error(make_task(_instrument(weights=[50, 20])))
    assert "balance" in msg


def test_balance_weight_multiple_of_smallest():
    # step — наименьшая гиря набора: гиря 2.5 при step 1 не из разновеса.
    msg = load_error(make_task(_balance(weights=[50, 2.5])))
    assert "multiple of step" in msg


def test_balance_weights_within_limit():
    msg = load_error(make_task(_balance(weights=[100, 100, 50], value=200)))
    assert "weighing limit" in msg


def test_balance_at_most_four_weights():
    msg = load_error(make_task(_balance(weights=[50, 20, 10, 5, 2], value=87)))
    assert "4" in msg


def test_balance_min_is_zero():
    msg = load_error(make_task(_balance(min=5)))
    assert "start at 0" in msg


def test_balance_pan_combinations_are_legal():
    # Чашки комбинируются свободно под тип задачи: тело + пустая чаша
    # («какие гири положить?»), только гири, пустые весы, гири с повторами.
    parse_block(make_task(_balance(value=80, weights=None)))
    parse_block(make_task(_balance(value=None, weights=[100])))
    parse_block(make_task(_balance(value=None, weights=None)))
    parse_block(make_task(_balance(value=70, weights=[50, 10, 10])))


# --- Обязательные поля, закрытые словари, опечатки, дубли ---


def test_graph_missing_range_has_path():
    msg = load_error(make_task({"type": "graph", "x_label": "t", "y_label": "v",
                                "y_range": [0, 1]}))
    assert "x_range" in msg and "blocks[0]" in msg



def test_choice_missing_options_has_path():
    msg = load_error(make_task({"type": "choice", "select": "single"}))
    assert "options" in msg and "blocks[0]" in msg



def test_degenerate_range_rejected_at_load():
    msg = load_error(make_task({"type": "graph", "x_label": "t", "y_label": "v",
                                "x_range": [2, 2], "y_range": [0, 1]}))
    assert "x_range" in msg



def test_list_bogus_marker_rejected():
    msg = load_error(make_task({"type": "list", "items": ["а"],
                                "marker": "bogus", "columns": "three"}))
    assert "marker" in msg or "columns" in msg



def test_series_bogus_style_rejected():
    msg = load_error(make_task({"type": "graph", "x_label": "t", "y_label": "v",
                                "x_range": [0, 1], "y_range": [0, 1],
                                "series": [{"points": [[0, 0], [1, 1]], "style": "wavy"}]}))
    assert "style" in msg



def test_typo_field_rejected():
    # Опечатка в имени поля не должна молча игнорироваться.
    msg = load_error(make_task({"type": "choice", "select": "multiple", "options": [
        {"text": "а", "corect": True}, {"text": "б", "correct": True},
    ]}))
    assert "corect" in msg



def test_duplicate_block_ids_rejected():
    msg = load_error(make_task(
        {"type": "text", "body": "а", "id": "dup"},
        {"type": "open", "id": "dup"},
    ))
    assert "dup" in msg



def test_too_many_parts_rejected_at_load():
    parts = [
        {"type": "part", "blocks": [{"type": "open"}]}
        for _ in range(40)
    ]
    msg = load_error(make_task(*parts))
    assert "part" in msg.lower()


def test_duplicate_explicit_labels_rejected():
    # Два part с label "а" напечатали бы "а) ... а)".
    msg = load_error(make_task(
        {"type": "part", "label": "а", "blocks": [{"type": "open"}]},
        {"type": "part", "label": "а", "blocks": [{"type": "open"}]},
    ))
    assert "unique" in msg


def test_label_outside_letters_rejected():
    msg = load_error(make_task(
        {"type": "part", "label": "Z9", "blocks": [{"type": "open"}]},
    ))
    assert "label" in msg


def test_zero_points_rejected():
    # points: 0 раньше проходил валидацию, но молча не печатался.
    msg = load_error(make_task({"type": "open"}, points=0))
    assert "points" in msg
    msg = load_error(make_task(
        {"type": "part", "points": 0, "blocks": [{"type": "open"}]},
    ))
    assert "points" in msg


def test_bar_y_range_must_start_at_zero():
    # Столбик от ненулевого основания врёт о соотношении высот.
    msg = load_error(make_task({"type": "graph", "chart_type": "bar",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [10, 50],
                                "series": [{"points": [[1, 20]]}]}))
    assert "start at 0" in msg
    msg = load_error(make_task({"type": "plot", "chart_type": "bar",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [10, 50],
                                "answer": [{"points": [[1, 20]]}]}))
    assert "start at 0" in msg
