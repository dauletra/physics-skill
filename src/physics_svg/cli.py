"""Command line: one entry point, three things it can make.

    physics-svg build <draft>            document.html (bodies + answers + draft)
    physics-svg build <draft> --handout  the same document without answers
    physics-svg build <draft> --format docx   the same document as a Word file
    physics-svg build <draft> --block ID a preview of one block
    physics-svg visual <spec.json>       one standalone SVG
    physics-svg schema                   the published JSON Schema

Validation problems are printed as a plain list with the path to each — no
traceback. A teacher (or the model working for one) fixes the whole draft in
one pass.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from physics_svg import __version__
from physics_svg.document import (
    WorkspaceError,
    build_document,
    build_docx,
    build_preview,
    load_workspace,
)
from physics_svg.document.blocks import doc_block_annotation
from physics_svg.document.emit.docx import Unsupported
from physics_svg.draw import SCREEN_SCALE
from physics_svg.schema import SchemaError, emit_schema
from physics_svg.visuals import build_svg, parse_visual, visual_annotation

#: Output formats, named once: SKILL.md tells the model about them, and the
#: bundle test checks it promises nothing this list does not have.
FORMATS = ("html", "docx", "both")


def main(argv: list[str] | None = None) -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(prog="physics-svg", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="собрать документ из папки-черновика")
    build.add_argument("draft", help="папка с document.json и blocks/")
    build.add_argument(
        "--format",
        default="html",
        choices=list(FORMATS),
        help="html — страница для просмотра и продолжения работы, "
        "docx — файл Word для правки руками и печати",
    )
    build.add_argument(
        "--handout",
        action="store_true",
        help="раздаточный вариант: без секции ответов и без встроенного черновика",
    )
    build.add_argument("--block", help="собрать превью одного блока по его id")
    build.add_argument("-o", "--out", help="куда положить результат (по умолчанию <draft>/output)")

    visual = commands.add_parser("visual", help="отрисовать одну иллюстрацию в самодостаточный SVG")
    visual.add_argument("spec", help="JSON-спека одного визуального блока")
    visual.add_argument("-o", "--out", help="выходной .svg (по умолчанию рядом со спекой)")
    visual.add_argument(
        "--scale", type=float, default=1.0, metavar="K",
        help="множитель размера: 2 — вдвое крупнее, шрифты и линии растут пропорционально",
    )

    schema = commands.add_parser("schema", help="напечатать JSON Schema документа и иллюстраций")
    schema.add_argument("-o", "--out", help="файл вместо стандартного вывода")

    args = parser.parse_args(argv)
    handlers = {"build": _build, "visual": _visual, "schema": _schema}
    try:
        return handlers[args.command](args)
    except (WorkspaceError, SchemaError) as error:
        print(str(error), file=sys.stderr)
        return 1


def _force_utf8_output() -> None:
    """Messages are Russian; a Windows console defaults to a code page that
    mangles them. Reconfiguring the streams makes output identical everywhere,
    which matters because the model reads these messages."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def _build(args: argparse.Namespace) -> int:
    draft = Path(args.draft)
    workspace = load_workspace(draft)

    if args.block:
        if args.handout:
            print(
                "--handout не используется с --block: превью всегда показывает ответы",
                file=sys.stderr,
            )
            return 2
        try:
            html = build_preview(workspace.document, workspace.blocks, args.block)
        except KeyError:
            print(f"блок '{args.block}' не найден в document.json -> order", file=sys.stderr)
            return 1
        destination = Path(args.out) if args.out else draft / f"{args.block}.preview.html"
        return _write(destination, html)

    output_dir = Path(args.out) if args.out else draft / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    name = "document-handout" if args.handout else "document"
    answers = not args.handout

    status = 0
    if args.format in ("html", "both"):
        # No embedded draft in a handout: it would reveal the answers through
        # the page source, which is the one place it must not leak them.
        source = None if args.handout else workspace.source
        html = build_document(
            workspace.document, workspace.blocks, with_answers=answers, source=source
        )
        status = _write(output_dir / f"{name}.html", html)
    if args.format in ("docx", "both"):
        try:
            result = build_docx(workspace.document, workspace.blocks, with_answers=answers)
        except Unsupported as error:
            print(str(error), file=sys.stderr)
            return 1
        status = _write_bytes(output_dir / f"{name}.docx", result.data) or status
        _report(result.notes)
    return status


def _report(notes: tuple[str, ...]) -> None:
    """What the Word file could not express, said out loud.

    The document is finished and correct; these are the formulas printed as
    plain text because they are outside the OMML subset. Silence here would
    mean a teacher finding `\\int` on the sheet after printing thirty copies.
    """
    if not notes:
        return
    print("Формулы, которые Word не понял (вставлены текстом):", file=sys.stderr)
    for note in notes:
        print(f"  {note}", file=sys.stderr)


def _visual(args: argparse.Namespace) -> int:
    spec_path = Path(args.spec)
    if not spec_path.exists():
        print(f"не найдена спека: {spec_path}", file=sys.stderr)
        return 1
    if args.scale <= 0:
        print("--scale должен быть положительным", file=sys.stderr)
        return 2
    model = parse_visual(json.loads(spec_path.read_text(encoding="utf-8")), spec_path.name)
    svg = build_svg(model, standalone=True, scale=SCREEN_SCALE * args.scale)
    return _write(Path(args.out) if args.out else spec_path.with_suffix(".svg"), svg)


def _schema(args: argparse.Namespace) -> int:
    schema = emit_schema(
        {"block": doc_block_annotation(), "visual": visual_annotation()},
        title="physics-svg: блок документа и иллюстрация",
    )
    text = json.dumps(schema, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        return _write(Path(args.out), text)
    sys.stdout.write(text)
    return 0


def _write(path: Path, content: str) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Готово: {path}")
    return 0


def _write_bytes(path: Path, content: bytes) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    print(f"Готово: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
