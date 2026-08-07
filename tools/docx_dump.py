#!/usr/bin/env python3
"""Print a part of a .docx package with indentation.

A Word file is a zip of XML written in one long line, and Word says nothing
useful about what it dislikes. When a paragraph comes out with the wrong
indent or a table loses its header, the answer is in `word/document.xml` —
this prints it in a form a person can read and a diff can show.

The eye-level counterpart of `contact_sheet.py`: that one shows how the sheet
looks, this one shows what was written.

    python tools/docx_dump.py <черновик>                 # собрать и напечатать
    python tools/docx_dump.py document.docx              # word/document.xml
    python tools/docx_dump.py document.docx --part word/styles.xml
    python tools/docx_dump.py document.docx --list       # что вообще в пакете
    python tools/docx_dump.py <черновик> -o before.xml   # чтобы сравнить потом
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path
from xml.dom import minidom

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from physics_svg.document import build_docx, load_workspace  # noqa: E402

DEFAULT_PART = "word/document.xml"


def package_bytes(source: Path) -> bytes:
    """A .docx as given, or one built from a draft folder on the spot.

    Building here rather than asking for a file first is the whole
    convenience: what a contributor has after an edit is the draft.
    """
    if source.is_dir():
        workspace = load_workspace(source)
        return build_docx(workspace.document, workspace.blocks)
    return source.read_bytes()


def parts(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        return sorted(package.namelist())


def dump(data: bytes, part: str) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as package:
        if part not in package.namelist():
            raise SystemExit(
                f"в пакете нет части '{part}'; есть: " + ", ".join(parts(data))
            )
        xml = package.read(part).decode("utf-8")
    # The same formatting the golden test uses, so a dump and a golden can be
    # compared directly.
    return minidom.parseString(xml).toprettyxml(indent="  ")


def main() -> None:
    # Messages and the XML itself are not ASCII; a Windows console defaults to
    # a code page that mangles both. Same reconfiguration as the CLI does.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="файл .docx или папка-черновик (соберётся на лету)")
    parser.add_argument(
        "--part", default=DEFAULT_PART, help=f"часть пакета (по умолчанию {DEFAULT_PART})"
    )
    parser.add_argument("--list", action="store_true", help="перечислить части пакета и выйти")
    parser.add_argument("-o", "--out", help="файл вместо стандартного вывода")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"не найдено: {source}")
    data = package_bytes(source)

    text = "\n".join(parts(data)) + "\n" if args.list else dump(data, args.part)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Готово: {args.out}")
        return
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        # `| head` closed the pipe. Nothing went wrong; a traceback on a
        # dump piped somewhere is just noise.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())


if __name__ == "__main__":
    main()
