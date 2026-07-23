"""Проверки уровня workspace (cli.load_workspace): ошибки, которые не видны
на уровне одного файла блока — файл вне document.order (молча выпал бы из
документа), несовпадение id с именем файла. Все ошибки собираются одним
списком, как и ошибки валидации блоков."""
import json

import pytest

from worksheet_builder.cli import load_workspace


def make_workspace(tmp_path, order, files):
    (tmp_path / "blocks").mkdir()
    (tmp_path / "document.json").write_text(
        json.dumps({"title": "T", "order": order}), encoding="utf-8"
    )
    for name, block in files.items():
        (tmp_path / "blocks" / f"{name}.json").write_text(
            json.dumps(block, ensure_ascii=False), encoding="utf-8"
        )
    return tmp_path


def minimal(block_id):
    return {"type": "task", "id": block_id, "blocks": [
        {"type": "text", "body": "Условие."},
        {"type": "open"},
    ]}


def load_exit(ws) -> str:
    with pytest.raises(SystemExit) as excinfo:
        load_workspace(ws)
    return str(excinfo.value)


def test_unlisted_block_file_is_an_error(tmp_path):
    # Файл есть в blocks/, но не в order — молча выпал бы из документа.
    ws = make_workspace(tmp_path, ["task-01"], {
        "task-01": minimal("task-01"),
        "task-02": minimal("task-02"),
    })
    msg = load_exit(ws)
    assert "task-02" in msg and "order" in msg


def test_id_must_match_file_name(tmp_path):
    ws = make_workspace(tmp_path, ["task-01"], {
        "task-01": minimal("task-99"),
    })
    msg = load_exit(ws)
    assert "task-99" in msg and "task-01" in msg


def test_workspace_errors_collected_together(tmp_path):
    # Несовпадение id, отсутствующий файл и файл вне order — одним списком.
    ws = make_workspace(tmp_path, ["task-01", "task-03"], {
        "task-01": minimal("task-99"),
        "task-02": minimal("task-02"),
    })
    msg = load_exit(ws)
    assert "task-99" in msg          # id != имя файла
    assert "task-03" in msg          # файла нет
    assert "task-02" in msg          # файл вне order


def test_valid_workspace_loads(tmp_path):
    ws = make_workspace(tmp_path, ["task-01", "task-02"], {
        "task-01": minimal("task-01"),
        "task-02": minimal("task-02"),
    })
    doc, raw_doc, raw_blocks = load_workspace(ws)
    assert [b["id"] for b in raw_blocks] == ["task-01", "task-02"]
    assert raw_doc["title"] == "T"


def test_no_order_takes_all_files_sorted(tmp_path):
    ws = make_workspace(tmp_path, None, {
        "task-02": minimal("task-02"),
        "task-01": minimal("task-01"),
    })
    doc, raw_doc, raw_blocks = load_workspace(ws)
    assert [b["id"] for b in raw_blocks] == ["task-01", "task-02"]


def test_order_duplicates_rejected(tmp_path):
    ws = make_workspace(tmp_path, ["task-01", "task-01"], {
        "task-01": minimal("task-01"),
    })
    msg = load_exit(ws)
    assert "duplicates" in msg
