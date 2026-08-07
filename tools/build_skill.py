#!/usr/bin/env python3
"""Assemble the distributable skill bundle.

The bundle is a **build output**, not a directory in the repository. That is
what lets everything derivable be derived: the reference files are assembled
from the type registries, the index tables in SKILL.md are generated, the
example library is the same specs the tests render, and the version is
stamped in. A promise SKILL.md makes about a file that does not ship is
caught here rather than by a teacher.

    python tools/build_skill.py                 -> dist/skill/ + dist/*.zip
    python tools/build_skill.py --no-zip        -> just the directory
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from physics_svg import __version__  # noqa: E402
from physics_svg.document.blocks import doc_block_annotation  # noqa: E402
from physics_svg.document.components import (  # noqa: E402
    AnswerLineSpec,
    HeadingSpec,
    ListSpec,
    TableSpec,
    TextSpec,
)
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.schema import emit_schema  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402
from physics_svg.visuals import visual_annotation  # noqa: E402

BUNDLE_NAME = "physics-materials"
SOURCE = REPO / "skill"
PACKAGE = REPO / "src" / "physics_svg"
EXAMPLES = REPO / "examples"

#: Generated junk that must never reach a teacher's machine.
JUNK_DIRS = {"__pycache__", "output", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
JUNK_SUFFIXES = (".pyc", ".preview.html", ".svg.tmp")

#: Paths mentioned in SKILL.md that have to exist in the bundle.
MENTIONED_PATH = re.compile(r"\b((?:references|scripts|examples|library|physics_svg)/[\w./-]*\w)")

#: One-line descriptions for the index tables: the first paragraph of a
#: type's card, so the table and the gallery never disagree.
_FIRST_PARAGRAPH = re.compile(r"^#[^\n]*\n+(.+?)(?:\n\n|$)", re.S)

#: The front matter is the only part of the skill read before it triggers,
#: and it is cut at this length. Silently losing the tail would cost the
#: examples that make the skill fire at all.
_DESCRIPTION_LIMIT = 1024
_DESCRIPTION = re.compile(r"^description:[ \t]*(.+)$", re.M)


def build(destination: Path, make_zip: bool = True) -> Path:
    root = destination / BUNDLE_NAME
    if destination.exists():
        shutil.rmtree(destination)
    root.mkdir(parents=True)

    _write_references(root / "references")
    _write_skill_md(root / "SKILL.md")
    _copy_tree(SOURCE / "scripts", root / "scripts")
    _copy_tree(PACKAGE, root / "physics_svg")
    _copy_tree(EXAMPLES, root / "examples")
    _write_library(root / "library")
    _write_schema(root / "schema.json")
    (root / "VERSION").write_text(f"{__version__}\n", encoding="utf-8")

    _check_promises(root)
    if not make_zip:
        return root

    archive = destination / f"{BUNDLE_NAME}-skill.zip"
    files = sorted(p for p in root.rglob("*") if p.is_file())
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, f"{BUNDLE_NAME}/{path.relative_to(root).as_posix()}")
    print(f"Собрано {len(files)} файлов -> {archive} ({archive.stat().st_size / 1024:.0f} КБ)")
    return archive


# --- generated references ----------------------------------------------


def _write_references(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "document.md").write_text(
        _fill(
            (SOURCE / "references" / "document.md").read_text(encoding="utf-8"),
            {"COMPONENT_TABLE": _component_table(), "QUESTION_TABLE": _question_index()},
        ),
        encoding="utf-8",
    )
    shutil.copy2(SOURCE / "references" / "symbols.md", directory / "symbols.md")
    (directory / "questions.md").write_text(
        _concatenate(
            "Виды вопросов",
            "У каждого вида — свои естественные поля и правильный ответ инлайн, "
            "рядом с содержимым, к которому он относится. Общее у всех: `type`, "
            "необязательные `id` и `explanation`.",
            [entry.doc for entry in load_questions().values()],
        ),
        encoding="utf-8",
    )
    (directory / "slides.md").write_text(
        _concatenate(
            "Виды слайдов",
            "Презентация сверху — плоский список слайдов; порядок в списке и есть "
            "порядок показа. У каждого вида свои поля, общее — `type` и "
            "необязательный `id`. Раскладку слайд не задаёт: где встанет "
            "картинка и когда откроется ответ, решает плеер.",
            [entry.doc for entry in load_slides().values()],
        ),
        encoding="utf-8",
    )
    (directory / "visuals.md").write_text(
        _concatenate(
            "Иллюстрации",
            "Задаются данными, а не рисунком. Одна и та же спека годится и как "
            "блок внутри документа, и как отдельный SVG-файл. Готовые примеры — "
            "в `library/<тип>/`.",
            [entry.doc("doc.md") for entry in load_visuals().values()],
        ),
        encoding="utf-8",
    )


def _concatenate(title: str, intro: str, fragments: list[Path]) -> str:
    parts = [f"# {title}\n\n{intro}\n"]
    for fragment in fragments:
        text = fragment.read_text(encoding="utf-8").strip()
        # Fragments are standalone pages with their own H1; nested under one
        # title every level moves down by one, so the outline stays valid.
        parts.append("\n" + re.sub(r"^(#{1,5}) ", r"#\1 ", text, flags=re.M) + "\n")
    return "\n".join(parts)


def _component_table() -> str:
    rows = [
        ("text", "абзац текста: условие, объяснение, определение"),
        ("heading", "подзаголовок раздела документа"),
        ("list", "список пунктов, с маркером или без"),
        ("table", "таблица с подписанными колонками"),
        ("answer_line", "строка «Ответ: ______» под короткий ответ"),
    ]
    known = {TextSpec, HeadingSpec, ListSpec, TableSpec, AnswerLineSpec}
    assert len(known) == len(rows), "таблица компонентов разошлась с модулем components"
    rows += [(entry.tag, _summary(entry.doc("card.md"))) for entry in load_visuals().values()]
    return _table(("тип", "что это"), rows)


def _question_index() -> str:
    return _table(
        ("тип", "что это"),
        [(entry.tag, entry.title.lower()) for entry in load_questions().values()],
    )


#: An index line has to stay one line. Failing the build is better than
#: truncating: the fix belongs in the card, which should open with a summary.
_SUMMARY_LIMIT = 90


def _summary(card: Path) -> str:
    text = card.read_text(encoding="utf-8")
    match = _FIRST_PARAGRAPH.search(text)
    sentence = " ".join(match.group(1).split()).split(".")[0] if match else ""
    if len(sentence) > _SUMMARY_LIMIT:
        raise SystemExit(
            f"{card.relative_to(REPO)}: первое предложение длиннее {_SUMMARY_LIMIT} символов "
            f"({len(sentence)}) — карточка должна открываться коротким описанием, "
            "оно идёт в индекс справочника"
        )
    return sentence.lower()


def _table(header: tuple[str, str], rows: list[tuple[str, str]]) -> str:
    lines = [f"| {header[0]} | {header[1]} |", "|---|---|"]
    lines += [f"| `{tag}` | {description} |" for tag, description in rows]
    return "\n".join(lines)


def _write_skill_md(destination: Path) -> None:
    text = _fill(
        (SOURCE / "SKILL.md").read_text(encoding="utf-8"),
        {
            "VERSION": __version__,
            "QUESTION_COUNT": str(len(load_questions())),
            "VISUAL_COUNT": str(len(load_visuals())),
            "SLIDE_COUNT": str(len(load_slides())),
        },
    )
    _check_description(text)
    destination.write_text(text, encoding="utf-8")


def _check_description(text: str) -> None:
    match = _DESCRIPTION.search(text)
    if match is None:
        raise SystemExit("в SKILL.md нет поля 'description' — без него скилл не находится")
    length = len(match.group(1).strip())
    if length > _DESCRIPTION_LIMIT:
        raise SystemExit(
            f"description в SKILL.md — {length} символов при лимите {_DESCRIPTION_LIMIT}: "
            f"убери {length - _DESCRIPTION_LIMIT}, начиная с перечисления возможностей "
            "(оно и так в теле скилла), а примеры формулировок оставь"
        )


def _fill(template: str, values: dict[str, str]) -> str:
    def replace(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in values:
            raise SystemExit(f"в шаблоне встретился неизвестный плейсхолдер {{{{{name}}}}}")
        return values[name]

    return re.sub(r"\{\{(\w+)\}\}", replace, template)


# --- library, schema, plumbing -----------------------------------------


def _write_library(directory: Path) -> None:
    """The example specs, shipped so the model edits one instead of inventing."""
    for entry in load_visuals().values():
        target = directory / entry.tag
        target.mkdir(parents=True, exist_ok=True)
        for spec in entry.specs:
            shutil.copy2(spec, target / spec.name)


def _write_schema(destination: Path) -> None:
    import json

    schema = emit_schema(
        {"block": doc_block_annotation(), "visual": visual_annotation()},
        title="physics-svg: блок документа и иллюстрация",
    )
    destination.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _copy_tree(source: Path, destination: Path) -> None:
    shutil.copytree(source, destination, ignore=_ignore_junk)


def _ignore_junk(directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name in JUNK_DIRS
        or name.startswith(".")
        or name.endswith(JUNK_SUFFIXES)
        or name.endswith(".egg-info")
    }


def _check_promises(root: Path) -> None:
    """SKILL.md must not point at anything the teacher will not have."""
    text = (root / "SKILL.md").read_text(encoding="utf-8")
    missing = []
    for mentioned in sorted(set(MENTIONED_PATH.findall(text))):
        target = root / mentioned
        if not target.exists() and not target.parent.exists():
            missing.append(mentioned)
    if missing:
        raise SystemExit(
            "SKILL.md обещает пути, которых нет в бандле:\n  " + "\n  ".join(missing)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist/skill", help="куда собирать (по умолчанию dist/skill)")
    parser.add_argument("--no-zip", action="store_true", help="только папка, без архива")
    args = parser.parse_args()
    result = build(REPO / args.out, make_zip=not args.no_zip)
    print(f"Готово: {result}")


if __name__ == "__main__":
    main()
