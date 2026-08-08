#!/usr/bin/env python3
"""Generate the documentation site from the registries.

The site is for **teachers**, and it is generated from the same code that
produces what a teacher receives: every picture in the gallery is drawn by
the renderer from a spec the tests also render, and every example of a task
kind is rendered by the document renderer itself. A screenshot cannot go
stale here, because there are no screenshots.

Hand-written pages (`docs/index.md`, `docs/install.md`, `docs/contribute.md`
and the two design documents) are left alone.

    python tools/build_site.py     # then: zensical serve
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "tools"))

import build_skill  # noqa: E402
from physics_svg.document import (  # noqa: E402
    build_document,
    build_docx,
    parse_block,
    parse_document,
)
from physics_svg.document.assets import BASE_CSS  # noqa: E402
from physics_svg.document.questions import QuestionType  # noqa: E402
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.presentation import build_data, build_page  # noqa: E402
from physics_svg.presentation import load_workspace as load_lesson  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.visuals import VisualType, build_svg, parse_visual  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402

DOCS = REPO / "docs"
GENERATED = [DOCS / "gallery", DOCS / "reference", DOCS / "assets"]

EXAMPLE = REPO / "examples" / "kinematics-9th-grade"

#: Everything the document renderer emits is class-based, so its stylesheet
#: can be scoped under one wrapper and dropped straight into a themed page.
PREVIEW_CLASS = "doc-preview"

_RULE = re.compile(r"([^{}]+)\{([^}]*)\}", re.S)

#: How a gallery card pins a picture into its text: a fenced block naming an
#: example spec by file stem. The same convention as the question references,
#: where a fenced block is the machine-readable part of a human page.
SPEC_FENCE = re.compile(r"^```spec\n(.+?)\n```[ \t]*$", re.M)


def main() -> None:
    for directory in GENERATED:
        if directory.exists():
            shutil.rmtree(directory)
        directory.mkdir(parents=True)

    bundle = build_skill.build(REPO / "dist" / "skill", make_zip=True)
    _copy_download(bundle)
    _write_example()
    families = _write_gallery()
    _write_questions()
    _write_slides()
    pages = _mirror_reference()
    _check_nav(families)
    print(f"Готово: галерея ({len(families)}), справочники ({len(pages)}), примеры")


def _check_nav(families: list[str]) -> None:
    """A new illustration must reach the menu, not just the disk.

    `zensical build --strict` warns about an orphan page, but only after the
    site is generated; failing here points at the file to edit.
    """
    nav = (REPO / "zensical.toml").read_text(encoding="utf-8")
    pages = [f"gallery/{tag}.md" for tag in families] + ["questions.md", "slides.md"]
    missing = [page for page in pages if f'"{page}"' not in nav]
    if missing:
        raise SystemExit(
            "сгенерированные страницы не перечислены в nav (zensical.toml): "
            + ", ".join(missing)
        )


# --- downloads and the full example ------------------------------------


def _copy_download(archive: Path) -> None:
    """The zip a teacher installs, served from the site itself."""
    shutil.copy2(archive, DOCS / "assets" / archive.name)


def _write_example() -> None:
    """The worked example as the real artefact, not a description of one.

    In both formats, because both are what a teacher gets: the page to look at
    and print, and the Word file to edit by hand. Downloading the .docx is the
    only way to see what the second backend actually produces before
    installing anything.
    """
    from physics_svg.document import load_workspace

    workspace = load_workspace(EXAMPLE)
    (DOCS / "assets" / "example-document.html").write_text(
        build_document(workspace.document, workspace.blocks, source=workspace.source),
        encoding="utf-8",
    )
    (DOCS / "assets" / "example-handout.html").write_text(
        build_document(workspace.document, workspace.blocks, with_answers=False),
        encoding="utf-8",
    )
    (DOCS / "assets" / "example-document.docx").write_bytes(
        build_docx(workspace.document, workspace.blocks).data
    )
    # The lesson's second draft, built by the same command a teacher runs.
    # Nothing on the site describes what a slide looks like — the page links
    # to the presentation itself, and the player draws it.
    lesson = load_lesson(EXAMPLE)
    (DOCS / "assets" / "example-presentation.html").write_text(
        build_page(build_data(lesson.presentation, lesson.slides)), encoding="utf-8"
    )


# --- gallery ------------------------------------------------------------


def _write_gallery() -> list[str]:
    pages = []
    for entry in load_visuals().values():
        (DOCS / "gallery" / f"{entry.tag}.md").write_text(_gallery_page(entry), encoding="utf-8")
        pages.append(entry.tag)
        print(f"  gallery/{entry.tag}.md ({len(entry.specs)} шт.)")
    return pages


def _gallery_page(entry: VisualType) -> str:
    """The teacher's card, with each spec drawn where the card asks for it.

    A card may place its own pictures — `SPEC_FENCE` marks the spot — and then
    the page is a tour through cases instead of a list of files. That is worth
    the parsing for a type used as often as `graph`; a card that places
    nothing keeps the plain listing, and one that places some of them still
    shows the rest, so a spec cannot go missing from the site.
    """
    card = entry.doc("card.md").read_text(encoding="utf-8").rstrip()
    drawn = {path.stem: _spec_block(entry, path) for path in entry.specs}
    parts: list[str] = []
    cursor = 0
    for match in SPEC_FENCE.finditer(card):
        stem = match.group(1).strip()
        if stem not in drawn:
            raise SystemExit(
                f"{entry.tag}/card.md: спеки '{stem}' нет; есть {', '.join(sorted(drawn))}"
            )
        parts += [card[cursor : match.start()], drawn.pop(stem)]
        cursor = match.end()
    parts.append(card[cursor:])
    parts += [f"\n### {stem}\n\n{block}" for stem, block in drawn.items()]
    return "\n".join(parts)


def _spec_block(entry: VisualType, spec_path: Path) -> str:
    """One rendered example: the picture, and the JSON behind it folded away."""
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    model = parse_visual(raw, spec_path.name)
    name = f"{entry.tag}-{spec_path.stem}.svg"
    (DOCS / "assets" / name).write_text(
        build_svg(model, scope=spec_path.stem, standalone=True), encoding="utf-8"
    )
    return (
        f"![{spec_path.stem}](../assets/{name})\n\n"
        f'??? note "Как это записано"\n\n'
        f"    ```json\n{_indent(raw)}\n    ```\n"
    )


def _indent(raw: object) -> str:
    text = json.dumps(raw, ensure_ascii=False, indent=2)
    return "\n".join("        " + line for line in text.splitlines())


# --- task kinds ---------------------------------------------------------


def _write_questions() -> None:
    """One page with every task kind, each shown as it will be printed."""
    parts = [
        "# Виды заданий\n",
        "Ниже — все виды, из которых собираются задания: как каждый выглядит "
        "на листе и что сказать Claude, чтобы получить такой.\n",
        "Правильные ответы в теле задания не печатаются никогда: рендерер "
        "собирает их в раздел «Ответы» в конце документа, а раздаточный "
        "вариант печатается вообще без него.\n",
        "Там, где ученик выбирает из готового набора — варианты теста, правый "
        "столбец, группы, слова для пропусков, — можно оставить лишние: они "
        "работают одинаково во всех таких заданиях. «Добавь пару лишних "
        "вариантов», «пусть одна группа останется пустой» — угадать станет "
        "нельзя.\n",
        f"<style>{_scoped_css()}</style>\n",
    ]
    for entry in load_questions().values():
        card = entry.card.read_text(encoding="utf-8").strip()
        parts.append(re.sub(r"^# ", "## ", card, flags=re.M))
        parts.append("")
        parts.extend(_previews(entry))
    (DOCS / "questions.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"  questions.md ({len(load_questions())} видов)")


def _write_slides() -> None:
    (DOCS / "slides.md").write_text(_slides_page(), encoding="utf-8")
    print(f"  slides.md ({len(load_slides())} видов)")


def _slides_page() -> str:
    """One page with every kind of slide — and the presentation itself.

    Here the site has to break its own habit: everything else on it is
    rendered by the code that renders what a teacher gets, but a slide is
    drawn by the player, in a browser, and a second renderer in Python is the
    one thing the design forbids. So the page shows the cards and opens the
    real built example instead of a picture of it.
    """
    parts = [
        "# Слайды презентации\n",
        "Презентация к уроку — то, что учитель показывает классу с проектора: "
        "тема, цели, объяснение, разбор задачи, задачи для доски, рефлексия. "
        "Это отдельный материал, а не лист на экране: содержимое у них разное, "
        "общие только иллюстрации.\n",
        "Ниже — виды слайдов, из которых она собирается, и что сказать Claude, "
        "чтобы получить такой. Как показывать готовую презентацию на уроке — "
        "на соседней странице [«Как показывать»](present.md).\n",
        "[Открыть пример презентации](assets/example-presentation.html)"
        "{ .md-button .md-button--primary }\n",
        "Картинка на слайде — из той же библиотеки, что и в заданиях: "
        "[графики](gallery/graph.md), приборы со шкалой, векторные диаграммы.\n",
    ]
    for entry in load_slides().values():
        card = entry.card.read_text(encoding="utf-8").strip()
        parts.append(re.sub(r"^# ", "## ", card, flags=re.M))
        parts.append("")
    return "\n".join(parts)


def _previews(entry: QuestionType) -> list[str]:
    """Render the kind's documented tasks through the real renderer.

    The same tasks the reference shows and the tests exercise — statement,
    question and place to write included — so a sheet on this page cannot
    show something the skill would not produce.
    """
    parts = []
    for task in entry.examples:
        html = build_document(parse_document({}), [parse_block(task, entry.tag)])
        body = html.split("<body>\n", 1)[1].split("\n</body>", 1)[0]
        parts.append(f'<div class="{PREVIEW_CLASS}" markdown="0">\n{body}\n</div>')
        parts.append("")
    return parts


def _scoped_css() -> str:
    """The document stylesheet, confined to one wrapper.

    Everything the renderer emits is class-based, so prefixing each selector
    is enough; the page-level rules become rules of the wrapper.

    Comments go first, before anything is split into rules: a comma inside a
    comment used to leave its tail glued to the next selector, and a browser
    drops a whole rule whose selector list it cannot parse — silently, so the
    previews stopped matching the printed sheet without failing the build.
    """
    scoped = []
    for match in _RULE.finditer(re.sub(r"/\*.*?\*/", "", BASE_CSS, flags=re.S)):
        selectors = [s.strip() for s in match.group(1).split(",") if s.strip()]
        body = match.group(2).strip()
        rewritten = []
        for selector in selectors:
            if selector.startswith("@"):
                continue
            if selector in (":root", "html", "body"):
                # Page-level rules describe the sheet itself — the wrapper.
                rewritten.append(f".{PREVIEW_CLASS}")
            elif selector == "*":
                rewritten.append(f".{PREVIEW_CLASS} *")
            else:
                rewritten.append(f".{PREVIEW_CLASS} {selector}")
        if rewritten and body:
            scoped.append(", ".join(rewritten) + " { " + body + " }")
    # The preview sits inside a themed page: no page margins, and a frame so
    # it reads as "this is what the sheet looks like".
    scoped.append(
        f".{PREVIEW_CLASS} {{"
        "max-width: none; margin: 1em 0; padding: 20px; border-radius: 8px;"
        "border: 1px solid var(--md-default-fg-color--lightest, #ddd);"
        "background: #fff; color: #000;"
        "}}".replace("{{", "{").replace("}}", "}")
    )
    return "\n".join(scoped)


# --- reference mirror ---------------------------------------------------


def _mirror_reference() -> list[str]:
    """The model-facing references, mirrored for people who want to read
    what the skill is actually told."""
    source = REPO / "dist" / "skill" / build_skill.BUNDLE_NAME / "references"
    pages = []
    note = (
        '!!! info "Это справочник для модели"\n\n'
        "    Страница собирается автоматически из того, что уходит в бандл "
        "скилла. Учителю она не нужна — смотрите «Галерею» и «Виды заданий».\n"
    )
    for path in sorted(source.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        if lines and lines[0].startswith("# "):
            text = "\n".join([lines[0], "", note, *lines[1:]])
        else:
            text = note + "\n" + text
        (DOCS / "reference" / path.name).write_text(text + "\n", encoding="utf-8")
        pages.append(path.name)
        print(f"  reference/{path.name}")
    return pages


if __name__ == "__main__":
    main()
