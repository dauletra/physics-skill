#!/usr/bin/env python3
"""Print a part of a .pptx package with indentation.

The mirror of `docx_dump.py`, and needed for the same reason twice over: a
deck is a zip of XML written in one long line, and PowerPoint says «в
презентации обнаружена ошибка» without naming the part it disliked. When a
slide comes up empty, when an animation does not run, when a layout is not
offered in «Создать слайд» — the answer is in one of these parts, and this
prints it in a form a person can read and a diff can show.

The default part is the first slide, because that is what is usually wrong.
`--list` is the fastest way to see what the deck is made of at all.

    python tools/pptx_dump.py <черновик>                   # собрать и напечатать
    python tools/pptx_dump.py урок.pptx                    # ppt/slides/slide1.xml
    python tools/pptx_dump.py урок.pptx --part ppt/slideLayouts/slideLayout7.xml
    python tools/pptx_dump.py урок.pptx --slide 4          # то же короче
    python tools/pptx_dump.py урок.pptx --list             # что вообще в пакете
    python tools/pptx_dump.py <черновик> -o before.xml     # чтобы сравнить потом
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

from physics_svg.presentation import load_workspace  # noqa: E402
from physics_svg.presentation.pptx.deck import build_deck  # noqa: E402

DEFAULT_PART = "ppt/slides/slide1.xml"


def package_bytes(source: Path) -> bytes:
    """A .pptx as given, or one built from a lesson folder on the spot.

    Building here rather than asking for a file first is the whole
    convenience: what a contributor has after an edit is the draft.
    """
    if source.is_dir():
        workspace = load_workspace(source)
        deck, _ = build_deck(workspace.presentation, workspace.slides)
        return deck
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
    parser.add_argument("source", help="файл .pptx или папка урока (соберётся на лету)")
    parser.add_argument(
        "--part", default=DEFAULT_PART, help=f"часть пакета (по умолчанию {DEFAULT_PART})"
    )
    parser.add_argument("--slide", type=int, help="номер слайда — короче, чем --part")
    parser.add_argument("--list", action="store_true", help="перечислить части пакета и выйти")
    parser.add_argument("-o", "--out", help="файл вместо стандартного вывода")
    args = parser.parse_args()

    source = Path(args.source)
    if not source.exists():
        raise SystemExit(f"не найдено: {source}")
    data = package_bytes(source)
    part = f"ppt/slides/slide{args.slide}.xml" if args.slide else args.part

    text = "\n".join(parts(data)) + "\n" if args.list else dump(data, part)
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
