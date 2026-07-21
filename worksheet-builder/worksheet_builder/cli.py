"""Рендерит черновик документа (document.json + blocks/*.json) в HTML.

Использование:
    python -m worksheet_builder <workspace_dir>
    python -m worksheet_builder <workspace_dir> --no-answers
    python -m worksheet_builder <workspace_dir> --block task-03
    python -m worksheet_builder --visual spec.json [-o out.svg]
    python -m worksheet_builder --emit-schema docs/document.schema.json

Первая форма пишет <workspace_dir>/output/document.html — единый итоговый
файл: тела всех блоков (теория, задания, их комбинации), секция «Ответы» в
конце и встроенный исходный черновик (`<script id="document-source">`) —
одного этого файла достаточно, чтобы продолжить правки в новой сессии.
Вторая (--no-answers) пишет document-no-answers.html — раздаточный вариант
без секции ответов и без встроенного черновика (он раскрыл бы ответы через
исходный код страницы). Третья — <workspace_dir>/task-03.preview.html
только с этим одним блоком, для дешёвой визуальной проверки. Четвёртая
рендерит спеку одного визуального блока (graph/instrument, та же схема, что
внутри документа) в самодостаточный .svg — иллюстрация без документа, для
показа в диалоге и вставки в презентацию (standalone.py). Пятая — JSON
Schema для автокомплита/проверки JSON в редакторе.

Ошибки валидации собираются по всем блокам и печатаются одним списком
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

from worksheet_builder.document import build_document, build_preview
from worksheet_builder.models import (
    DocBlockModel,
    DocumentModel,
    emit_json_schema,
    parse_block,
    parse_document,
    parse_visual,
)
from worksheet_builder.standalone import build_standalone_svg


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: невалидный JSON - {e}")


def load_workspace(workspace: str | Path) -> tuple[DocumentModel, Any, list[Any]]:
    """Возвращает (манифест-модель, сырой манифест, сырые блоки в порядке
    order).

    Сырые dict'ы нужны единственному потребителю — встраиванию черновика в
    итоговый HTML (см. document.render_source_script): туда должен попасть
    авторский JSON как есть, без нормализации моделью. Рендер по-прежнему
    работает только с моделями."""
    workspace = Path(workspace)
    doc_path = workspace / "document.json"
    if not doc_path.exists():
        sys.exit(f"document.json not found in {workspace}")
    raw_doc = _load_json(doc_path)
    try:
        doc = parse_document(raw_doc)
    except ValueError as e:
        sys.exit(str(e))
    blocks_dir = workspace / "blocks"
    available = sorted(p.stem for p in blocks_dir.glob("*.json"))
    order = doc.order or available
    errors = []
    # Файл, который есть в blocks/, но не перечислен в order, молча выпал бы
    # из документа — это ошибка сборки, а не «просто не показали».
    unlisted = sorted(set(available) - set(order))
    if unlisted:
        errors.append(
            "document.json -> order: block files exist but are not listed "
            f"(they would be silently dropped): {', '.join(unlisted)}"
        )
    raw_blocks = []
    for block_id in order:
        block_path = blocks_dir / f"{block_id}.json"
        if not block_path.exists():
            errors.append(f"Block file not found: {block_path}")
            continue
        raw = _load_json(block_path)
        raw_id = raw.get("id") if isinstance(raw, dict) else None
        if raw_id != block_id:
            errors.append(
                f"{block_path.name}: id {raw_id!r} does not match the file name (expected {block_id!r})"
            )
        raw_blocks.append(raw)
    if errors:
        sys.exit("\n".join(errors))
    return doc, raw_doc, raw_blocks


def parse_blocks(raw_blocks: list[Any]) -> list[DocBlockModel]:
    """Парсит все блоки, собирая ошибки валидации в один общий список —
    учитель (или Claude) чинит весь черновик за один прогон."""
    blocks, errors = [], []
    for raw in raw_blocks:
        try:
            blocks.append(parse_block(raw))
        except ValueError as e:
            errors.append(str(e))
    if errors:
        sys.exit("\n".join(errors))
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", nargs="?",
                        help="Path to the document draft folder (contains document.json, blocks/)")
    parser.add_argument("--no-answers", action="store_true",
                        help="Render the handout variant: no answers section, no embedded source")
    parser.add_argument("--block", help="Render only this single block id as a preview HTML")
    parser.add_argument("--visual", metavar="SPEC",
                        help="Render one visual block spec (graph/instrument JSON) "
                             "to a standalone SVG file")
    parser.add_argument("--scale", type=float, default=1.0, metavar="K",
                        help="Size multiplier for --visual output (e.g. 2 doubles "
                             "the rendered size; fonts scale proportionally)")
    parser.add_argument("-o", "--out", metavar="PATH",
                        help="Output file for --visual "
                             "(default: input file with .svg extension)")
    parser.add_argument("--emit-schema", metavar="PATH",
                        help="Write JSON Schema (document + block) to PATH and exit")
    args = parser.parse_args()

    if args.emit_schema:
        out = Path(args.emit_schema)
        out.write_text(json.dumps(emit_json_schema(), ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8")
        print(f"Wrote {out}")
        return

    if args.scale != 1.0 and not args.visual:
        parser.error("--scale is only used with --visual")

    if args.visual:
        if args.workspace or args.block:
            parser.error("--visual renders a single spec file; do not pass a workspace or --block")
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
    if args.out:
        parser.error("-o/--out is only used with --visual")

    if not args.workspace:
        parser.error("workspace is required (unless --visual or --emit-schema is used)")

    workspace = Path(args.workspace)
    doc, raw_doc, raw_blocks = load_workspace(workspace)
    blocks = parse_blocks(raw_blocks)

    if args.block:
        if args.no_answers:
            parser.error("--no-answers is not used with --block (a preview always shows answers)")
        try:
            html_doc = build_preview(doc, blocks, args.block)
        except KeyError:
            sys.exit(f"Block id '{args.block}' not found in document.json order")
        out_path = workspace / f"{args.block}.preview.html"
        out_path.write_text(html_doc, encoding="utf-8")
        print(f"Wrote {out_path}")
        return

    output_dir = workspace / "output"
    output_dir.mkdir(exist_ok=True)
    if args.no_answers:
        # Раздаточный вариант: без секции ответов и без встроенного черновика
        # (черновик раскрыл бы ответы через исходный код страницы).
        html = build_document(doc, blocks, with_answers=False)
        out_path = output_dir / "document-no-answers.html"
    else:
        # Полный вариант несёт встроенный черновик: этого файла достаточно,
        # чтобы вернуться к правкам в новой сессии.
        source = {"document": raw_doc, "blocks": raw_blocks}
        html = build_document(doc, blocks, with_answers=True, source=source)
        out_path = output_dir / "document.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
