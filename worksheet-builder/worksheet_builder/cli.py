"""Рендерит черновик рабочего листа (meta.json + tasks/*.json) в HTML.

Использование:
    python -m worksheet_builder <workspace_dir>
    python -m worksheet_builder <workspace_dir> --task task-03
    python -m worksheet_builder --emit-schema docs/task.schema.json

Первая форма пишет <workspace_dir>/output/worksheet-student.html и
worksheet-teacher.html. Вторая — <workspace_dir>/task-03.preview.html только
с этим одним заданием, для дешёвой визуальной проверки. Третья — JSON Schema
для автокомплита/проверки JSON в редакторе.

Ошибки валидации собираются по всем заданиям и печатаются одним списком
(каждая — с путём до блока), чтобы чинить всё за один прогон, а не по одной.

Сам конвейер рендеринга живёт в соседних модулях пакета (assets.py,
strings.py, render_helpers.py, visuals.py, models.py, document.py,
components.py, questions.py) — этот файл — просто CLI-точка входа.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any

from worksheet_builder.document import build_document
from worksheet_builder.models import (
    MetaModel,
    TaskModel,
    emit_json_schema,
    parse_meta,
    parse_task,
)


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: невалидный JSON - {e}")


def load_workspace(workspace: str | Path) -> tuple[MetaModel, list[Any]]:
    workspace = Path(workspace)
    meta_path = workspace / "meta.json"
    if not meta_path.exists():
        sys.exit(f"meta.json not found in {workspace}")
    try:
        meta = parse_meta(_load_json(meta_path))
    except ValueError as e:
        sys.exit(str(e))
    tasks_dir = workspace / "tasks"
    available = sorted(p.stem for p in tasks_dir.glob("*.json"))
    order = meta.order or available
    errors = []
    # Файл, который есть в tasks/, но не перечислен в order, молча выпал бы
    # из листа — это ошибка сборки, а не «просто не показали».
    unlisted = sorted(set(available) - set(order))
    if unlisted:
        errors.append(
            "meta.json -> order: task files exist but are not listed "
            f"(they would be silently dropped): {', '.join(unlisted)}"
        )
    raw_tasks = []
    for task_id in order:
        task_path = tasks_dir / f"{task_id}.json"
        if not task_path.exists():
            errors.append(f"Task file not found: {task_path}")
            continue
        raw = _load_json(task_path)
        raw_id = raw.get("id") if isinstance(raw, dict) else None
        if raw_id != task_id:
            errors.append(
                f"{task_path.name}: id {raw_id!r} does not match the file name (expected {task_id!r})"
            )
        raw_tasks.append(raw)
    if errors:
        sys.exit("\n".join(errors))
    return meta, raw_tasks


def parse_tasks(raw_tasks: list[Any]) -> list[TaskModel]:
    """Парсит все задания, собирая ошибки валидации в один общий список —
    учитель (или Claude) чинит весь черновик за один прогон."""
    tasks, errors = [], []
    for raw in raw_tasks:
        try:
            tasks.append(parse_task(raw))
        except ValueError as e:
            errors.append(str(e))
    if errors:
        sys.exit("\n".join(errors))
    return tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?",
                        help="Path to the worksheet draft folder (contains meta.json, tasks/)")
    parser.add_argument("--task", help="Render only this single task id as a preview HTML")
    parser.add_argument("--mode", choices=["student", "teacher"], default="teacher",
                        help="Variant for --task preview (default: teacher, i.e. with answers)")
    parser.add_argument("--emit-schema", metavar="PATH",
                        help="Write JSON Schema (meta + task) to PATH and exit")
    args = parser.parse_args()

    if args.emit_schema:
        out = Path(args.emit_schema)
        out.write_text(json.dumps(emit_json_schema(), ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"Wrote {out}")
        return
    if not args.workspace:
        parser.error("workspace is required (unless --emit-schema is used)")

    workspace = Path(args.workspace)
    meta, raw_tasks = load_workspace(workspace)
    tasks = parse_tasks(raw_tasks)

    if args.task:
        match = next((t for t in tasks if t.id == args.task), None)
        if match is None:
            sys.exit(f"Task id '{args.task}' not found in meta.json order")
        html_doc = build_document(meta, [match], is_teacher=(args.mode == "teacher"))
        out_path = workspace / f"{args.task}.preview.html"
        out_path.write_text(html_doc, encoding="utf-8")
        print(f"Wrote {out_path}")
        return

    output_dir = workspace / "output"
    output_dir.mkdir(exist_ok=True)
    student_html = build_document(meta, tasks, is_teacher=False)
    teacher_html = build_document(meta, tasks, is_teacher=True)
    (output_dir / "worksheet-student.html").write_text(student_html, encoding="utf-8")
    (output_dir / "worksheet-teacher.html").write_text(teacher_html, encoding="utf-8")
    print(f"Wrote {output_dir / 'worksheet-student.html'}")
    print(f"Wrote {output_dir / 'worksheet-teacher.html'}")


if __name__ == "__main__":
    main()
