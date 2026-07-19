"""Рендерит черновик рабочего листа (meta.json + tasks/*.json) в HTML.

Использование:
    python -m worksheet_builder <workspace_dir>
    python -m worksheet_builder <workspace_dir> --task task-03
    python -m worksheet_builder --visual spec.json [-o out.svg]
    python -m worksheet_builder --document doc.json [-o out.html]
    python -m worksheet_builder --emit-schema docs/task.schema.json

Первая форма пишет <workspace_dir>/output/worksheet-student.html и
worksheet-teacher.html; в тичер-вариант встраивается исходный черновик
(`<script id="worksheet-source">`) — одного этого файла достаточно, чтобы
продолжить правки в новой сессии. Вторая — <workspace_dir>/task-03.preview.html
только с этим одним заданием, для дешёвой визуальной проверки. Третья рендерит
спеку одного визуального блока (graph/instrument, та же схема, что внутри
задания) в самодостаточный .svg — иллюстрация без листа, для показа в диалоге
и вставки в презентацию (standalone.py). Четвёртая — документ без вопросов
(конспект/текст с иллюстрациями: title + компоненты + heading/row) в один HTML
со встроенным исходником (document.build_plain_document). Пятая — JSON Schema
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

from worksheet_builder.document import build_document, build_plain_document
from worksheet_builder.models import (
    MetaModel,
    TaskModel,
    emit_json_schema,
    parse_document,
    parse_meta,
    parse_task,
    parse_visual,
)
from worksheet_builder.standalone import build_standalone_svg


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: невалидный JSON - {e}")


def load_workspace(workspace: str | Path) -> tuple[MetaModel, Any, list[Any]]:
    """Возвращает (meta-модель, сырой meta, сырые задания в порядке order).

    Сырые dict'ы нужны единственному потребителю — встраиванию черновика в
    тичер-HTML (см. document.render_source_script): туда должен попасть
    авторский JSON как есть, без нормализации моделью. Рендер по-прежнему
    работает только с моделями."""
    workspace = Path(workspace)
    meta_path = workspace / "meta.json"
    if not meta_path.exists():
        sys.exit(f"meta.json not found in {workspace}")
    raw_meta = _load_json(meta_path)
    try:
        meta = parse_meta(raw_meta)
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
    return meta, raw_meta, raw_tasks


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
    parser.add_argument("--visual", metavar="SPEC",
                        help="Render one visual block spec (graph/instrument JSON) "
                             "to a standalone SVG file")
    parser.add_argument("--document", metavar="DOC",
                        help="Render a question-free document (title + component blocks "
                             "JSON) to a single HTML file")
    parser.add_argument("--scale", type=float, default=1.0, metavar="K",
                        help="Size multiplier for --visual output (e.g. 2 doubles "
                             "the rendered size; fonts scale proportionally)")
    parser.add_argument("-o", "--out", metavar="PATH",
                        help="Output file for --visual/--document "
                             "(default: input file with .svg/.html extension)")
    parser.add_argument("--emit-schema", metavar="PATH",
                        help="Write JSON Schema (meta + task) to PATH and exit")
    args = parser.parse_args()

    if args.emit_schema:
        out = Path(args.emit_schema)
        out.write_text(json.dumps(emit_json_schema(), ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"Wrote {out}")
        return

    if args.visual and args.document:
        parser.error("--visual and --document are mutually exclusive")

    if args.scale != 1.0 and not args.visual:
        parser.error("--scale is only used with --visual")

    if args.visual:
        if args.workspace or args.task:
            parser.error("--visual renders a single spec file; do not pass a workspace or --task")
        if args.scale <= 0:
            parser.error("--scale must be positive")
        spec_path = Path(args.visual)
        if not spec_path.exists():
            sys.exit(f"Visual spec not found: {spec_path}")
        try:
            model = parse_visual(_load_json(spec_path), spec_path.name)
        except ValueError as e:
            sys.exit(str(e))
        out_path = Path(args.out) if args.out else spec_path.with_suffix(".svg")
        out_path.write_text(build_standalone_svg(model, zoom=args.scale), encoding="utf-8")
        print(f"Wrote {out_path}")
        return

    if args.document:
        if args.workspace or args.task:
            parser.error("--document renders a single file; do not pass a workspace or --task")
        doc_path = Path(args.document)
        if not doc_path.exists():
            sys.exit(f"Document file not found: {doc_path}")
        raw = _load_json(doc_path)
        try:
            doc = parse_document(raw, doc_path.name)
        except ValueError as e:
            sys.exit(str(e))
        out_path = Path(args.out) if args.out else doc_path.with_suffix(".html")
        # Исходник встраивается всегда: у документа нет student-варианта,
        # прятать нечего, а продолжаемость правок — как у тичер-листа.
        out_path.write_text(build_plain_document(doc, source={"document": raw}),
                            encoding="utf-8")
        print(f"Wrote {out_path}")
        return
    if args.out:
        parser.error("-o/--out is only used with --visual or --document")

    if not args.workspace:
        parser.error(
            "workspace is required (unless --visual, --document or --emit-schema is used)"
        )

    workspace = Path(args.workspace)
    meta, raw_meta, raw_tasks = load_workspace(workspace)
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
    # Тичер-вариант несёт встроенный черновик: этого файла достаточно, чтобы
    # вернуться к правкам в новой сессии (у ученической версии черновика нет —
    # в нём ответы).
    source = {"meta": raw_meta, "tasks": raw_tasks}
    teacher_html = build_document(meta, tasks, is_teacher=True, source=source)
    (output_dir / "worksheet-student.html").write_text(student_html, encoding="utf-8")
    (output_dir / "worksheet-teacher.html").write_text(teacher_html, encoding="utf-8")
    print(f"Wrote {output_dir / 'worksheet-student.html'}")
    print(f"Wrote {output_dir / 'worksheet-teacher.html'}")


if __name__ == "__main__":
    main()
