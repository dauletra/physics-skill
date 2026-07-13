"""Негативная таблица: битый JSON задания → ValueError с внятным сообщением
и путём до блока, поднятая при загрузке (не traceback и не молчаливый
фолбэк). Вся валидация — pydantic-модели в models.py."""
import pytest

from worksheet_builder.models import parse_task


def load_error(task_dict) -> str:
    with pytest.raises(ValueError) as excinfo:
        parse_task(task_dict)
    return str(excinfo.value)


def make_task(*blocks, **extra):
    return {"id": "t-bad", "blocks": list(blocks), **extra}


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


def test_open_bad_response():
    msg = load_error(make_task({"type": "open", "response": "lines:zero"}))
    assert "lines" in msg


def test_bar_multiple_series():
    msg = load_error(make_task({"type": "graph", "chart_type": "bar",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [0, 5],
                                "series": [{"points": [[1, 1]]}, {"points": [[2, 2]]}]}))
    assert "single series" in msg


def test_unknown_chart_type():
    msg = load_error(make_task({"type": "graph", "chart_type": "pie",
                                "x_label": "x", "y_label": "y",
                                "x_range": [0, 5], "y_range": [0, 5]}))
    assert "chart_type" in msg


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
