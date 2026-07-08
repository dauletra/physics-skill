#!/usr/bin/env python3
"""Рендерит черновик рабочего листа (meta.json + tasks/*.json) в печатный HTML.

Использование:
    python render_worksheet.py <workspace_dir>
    python render_worksheet.py <workspace_dir> --task task-03

Первая форма пишет <workspace_dir>/output/worksheet-student.html и
worksheet-teacher.html. Вторая форма пишет <workspace_dir>/task-03.preview.html
только с этим одним заданием — для дешёвой визуальной проверки без полной пересборки.

Сам конвейер рендеринга живёт в соседних модулях этой папки (assets.py,
strings.py, render_helpers.py, visuals.py, components.py, document.py) —
этот файл — просто CLI-точка входа.
"""
import argparse
import json
import sys
from pathlib import Path

from document import build_document


def load_workspace(workspace):
    workspace = Path(workspace)
    meta_path = workspace / "meta.json"
    if not meta_path.exists():
        sys.exit(f"meta.json not found in {workspace}")
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    tasks_dir = workspace / "tasks"
    order = meta.get("order") or sorted(p.stem for p in tasks_dir.glob("*.json"))
    tasks = []
    for task_id in order:
        task_path = tasks_dir / f"{task_id}.json"
        if not task_path.exists():
            sys.exit(f"Task file not found: {task_path}")
        tasks.append(json.loads(task_path.read_text(encoding="utf-8")))
    return meta, tasks


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", help="Path to the worksheet draft folder (contains meta.json, tasks/)")
    parser.add_argument("--task", help="Render only this single task id as a preview HTML")
    args = parser.parse_args()

    workspace = Path(args.workspace)
    meta, tasks = load_workspace(workspace)

    if args.task:
        match = next((t for t in tasks if t.get("id") == args.task), None)
        if match is None:
            sys.exit(f"Task id '{args.task}' not found in meta.json order")
        html_doc = build_document(meta, [match], is_teacher=True)
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
