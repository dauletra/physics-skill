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
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))

from physics_svg import __version__  # noqa: E402
from physics_svg.document.components import (  # noqa: E402
    AnswerLineSpec,
    HeadingSpec,
    ListSpec,
    TableSpec,
    TextSpec,
)
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.presentation.slides import SlideTemplate, SlideType  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402

BUNDLE_NAME = "physics-materials"
SOURCE = REPO / "skill"
PACKAGE = REPO / "src" / "physics_svg"
EXAMPLES = REPO / "examples"

#: Generated junk that must never reach a teacher's machine.
JUNK_DIRS = {"__pycache__", "output", ".mypy_cache", ".pytest_cache", ".ruff_cache"}
JUNK_SUFFIXES = (".pyc", ".preview.html", ".svg.tmp")

#: How many files the bundle may hold. The uploader counts files, not bytes:
#: the archive weighs a third of a megabyte against a limit measured in tens,
#: and still got refused. A nested archive is one entry to it, which is why
#: the package ships as one — see `_write_package`.
FILE_LIMIT = 200

#: Paths mentioned in SKILL.md that have to exist in the bundle.
MENTIONED_PATH = re.compile(r"\b((?:references|scripts|examples|library|physics_svg)/[\w./-]*\w)")

#: One-line descriptions for the index tables: the first paragraph of a
#: type's card, so the table and the gallery never disagree.
_FIRST_PARAGRAPH = re.compile(r"^#[^\n]*\n+(.+?)(?:\n\n|$)", re.S)

#: How a slide's fragment pins a template into its text: a fenced block
#: naming it by file stem. The same convention as ```spec in a gallery card.
_TEMPLATE_FENCE = re.compile(r"^```template\n(.+?)\n```[ \t]*$", re.M)

#: Where a shipped template lands, and therefore what the model is told to copy.
_LIBRARY_SLIDES = "library/slides"

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
    _write_package(root / "physics_svg.zip")
    _copy_tree(EXAMPLES, root / "examples")
    _write_library(root / "library")
    (root / "VERSION").write_text(f"{__version__}\n", encoding="utf-8")

    _check_promises(root)
    _check_file_count(root)
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
            [_read(entry.doc) for entry in load_questions().values()],
        ),
        encoding="utf-8",
    )
    (directory / "slides.md").write_text(
        _concatenate(
            "Виды слайдов",
            "Презентация сверху — плоский список слайдов; порядок в списке и есть "
            "порядок показа. У каждого вида свои поля, общее — `type` и "
            "необязательный `id`. Раскладку слайд не задаёт: где встанет "
            "картинка и когда откроется ответ, решает показ. Читается, когда "
            "заготовки из `references/presentation.md` не хватило: работу над "
            "презентацией начинают там. У каждого вида показан один заполненный "
            "слайд целиком, остальные заготовки названы файлами — их содержимое "
            "лежит в `library/slides/<вид>/` и копируется оттуда, а не "
            "перепечатывается.",
            [_slide_fragment(entry) for entry in load_slides().values()],
        ),
        encoding="utf-8",
    )
    (directory / "presentation.md").write_text(
        _fill(
            (SOURCE / "references" / "presentation.md").read_text(encoding="utf-8"),
            {"SLIDE_COUNT": str(len(load_slides())), "TEMPLATE_TABLE": _template_table()},
        ),
        encoding="utf-8",
    )
    (directory / "visuals.md").write_text(
        _concatenate(
            "Иллюстрации",
            "Задаются данными, а не рисунком. Одна и та же спека годится и как "
            "блок внутри документа, и как отдельный SVG-файл. Готовые примеры — "
            "в `library/<тип>/`.",
            [_read(entry.doc("doc.md")) for entry in load_visuals().values()],
        ),
        encoding="utf-8",
    )


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _concatenate(title: str, intro: str, fragments: list[str]) -> str:
    parts = [f"# {title}\n\n{intro}\n"]
    for fragment in fragments:
        # Fragments are standalone pages with their own H1; nested under one
        # title every level moves down by one, so the outline stays valid.
        parts.append("\n" + re.sub(r"^(#{1,5}) ", r"#\1 ", fragment.strip(), flags=re.M) + "\n")
    return "\n".join(parts)


def _slide_fragment(entry: SlideType) -> str:
    """The kind's reference with its templates written out inside it.

    A fragment places a template where the prose wants it; what the prose
    does not place is appended at the end. That is the same deal a gallery
    card gets for its specs, and it has the same consequence: adding a
    template stays "add a file", and a template cannot go missing from the
    reference (docs/slide-templates.md §3).

    Only the **first** template of a kind is written out in full. The rest
    are named, because that is all the model needs of them: it copies the
    file out of `library/slides/`, it does not retype what the page shows.
    Printing all twenty-eight cost more than half of `slides.md`, and the
    twenty-seventh taught nothing the first had not — the shape of the kind
    is the same shape in every one of them.
    """
    text = _read(entry.doc).rstrip()
    remaining = {template.slug: template for template in entry.templates}
    written_in_full = False
    parts: list[str] = []
    cursor = 0
    for match in _TEMPLATE_FENCE.finditer(text):
        slug = match.group(1).strip()
        if slug not in remaining:
            raise SystemExit(
                f"{entry.tag}/doc.md: шаблона '{slug}' нет; "
                f"есть {', '.join(sorted(remaining))}"
            )
        parts += [
            text[cursor : match.start()],
            _template_block(entry, remaining.pop(slug), full=not written_in_full),
        ]
        written_in_full = True
        cursor = match.end()
    parts.append(text[cursor:])
    parts += [
        f"\n\n{_template_block(entry, template, full=False)}" for template in remaining.values()
    ]
    return "".join(parts)


def _template_block(entry: SlideType, template: SlideTemplate, *, full: bool) -> str:
    """One template as the model meets it: where to copy it from, when to
    take it, and — for the first one of its kind — what is inside. Written to
    stand where a fence stood, so it carries no blank lines of its own."""
    line = f"`{_LIBRARY_SLIDES}/{entry.tag}/{template.slug}.json` — {template.when}"
    if not full:
        return line
    return f"{line}\n\n```json\n{json.dumps(template.slide, ensure_ascii=False, indent=2)}\n```"


def _template_table() -> str:
    """Every template of every kind in one table — the cheap read before
    picking one, without the field tables of `slides.md`.

    It stands inside `presentation.md` rather than in a file of its own: the
    catalogue is the first thing the work needs and the last thing the page
    says, so the model that came for the workflow leaves with a template
    already chosen.
    """
    rows = [
        (f"{_LIBRARY_SLIDES}/{entry.tag}/{template.slug}.json", template.when)
        for entry in load_slides().values()
        for template in entry.templates
    ]
    return _table(("файл", "когда брать"), rows)


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
            "TEMPLATE_COUNT": str(
                sum(len(entry.templates) for entry in load_slides().values())
            ),
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


# --- library and plumbing ----------------------------------------------
#
# The JSON Schema used to ship here as `schema.json`. It stopped: nothing in
# SKILL.md or the references pointed at it, so it was 49 КБ nobody opened —
# and `render.py schema` prints the same thing on demand, from the same
# models, whenever anyone actually wants it.


def _write_library(directory: Path) -> None:
    """The example specs and slide templates, shipped so the model edits one
    instead of inventing.

    A template ships **unwrapped**: the envelope carries the name and the
    "when" for the catalogue, but what the model copies into `slides/` has to
    be a slide and nothing else.
    """
    for entry in load_visuals().values():
        target = directory / entry.tag
        target.mkdir(parents=True, exist_ok=True)
        for spec in entry.specs:
            shutil.copy2(spec, target / spec.name)
    for slide in load_slides().values():
        target = directory / "slides" / slide.tag
        target.mkdir(parents=True, exist_ok=True)
        for template in slide.templates:
            (target / template.path.name).write_text(
                json.dumps(template.slide, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )


def _write_package(archive: Path) -> None:
    """The package as one importable file, imported straight from the zip.

    Two reasons, and the second is the one that forced it. **Only modules
    ship**: the `specs/*.json`, `templates/*.json`, `doc.md` and `card.md`
    that live beside them in the source tree are already in `library/` and
    `references/`, and nothing reads them at run time — `VisualType.specs`,
    `SlideType.templates`, `.doc` and `.card` are properties the build, the
    suite and the site use, never the CLI. And **one file instead of a
    hundred and one**: the uploader counts files (FILE_LIMIT), a nested
    archive is one entry, and the two changes together take the bundle from
    329 files to 113.

    What it costs: a traceback from an unexpected crash keeps file names and
    line numbers but loses the source lines, because `linecache` will not
    read into a zip. Validation errors are unaffected — they are printed
    without a traceback either way. To see a line:

        python -c "import zipfile;print(zipfile.ZipFile('physics_svg.zip').read('physics_svg/cli.py').decode())"

    Timestamps are fixed rather than taken from the file system, so two
    builds of the same source are the same bytes and a release diff means
    something.
    """
    modules = sorted(
        path
        for path in PACKAGE.rglob("*.py")
        if not any(part in JUNK_DIRS for part in path.parts)
    )
    if not modules:
        raise SystemExit(f"в {PACKAGE} не нашлось ни одного модуля — пакет не соберётся")
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in modules:
            info = zipfile.ZipInfo(
                f"{PACKAGE.name}/{path.relative_to(PACKAGE).as_posix()}",
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            package.writestr(info, path.read_bytes())


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


def _check_file_count(root: Path) -> None:
    """The bundle has to fit through the uploader, and it grew past it once.

    Every other check here asks whether something is right; this one asks
    whether the teacher can install it at all. It failed silently before —
    the archive built, and the refusal came from claude.ai.
    """
    files = [path for path in root.rglob("*") if path.is_file()]
    if len(files) > FILE_LIMIT:
        raise SystemExit(
            f"в бандле {len(files)} файлов при лимите {FILE_LIMIT}: claude.ai такой "
            "архив не примет. Ищи, что уехало вторым экземпляром: спеки и заготовки "
            "уже лежат в library/, а doc.md — в references/"
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
