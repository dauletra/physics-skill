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
from physics_svg.document import build_document, parse_block, parse_document  # noqa: E402
from physics_svg.document.assets import BASE_CSS  # noqa: E402
from physics_svg.document.questions import QuestionType  # noqa: E402
from physics_svg.document.questions import load_all as load_questions  # noqa: E402
from physics_svg.visuals import build_svg, parse_visual  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402

DOCS = REPO / "docs"
GENERATED = [DOCS / "gallery", DOCS / "reference", DOCS / "assets"]

EXAMPLE = REPO / "examples" / "kinematics-9th-grade"

#: Everything the document renderer emits is class-based, so its stylesheet
#: can be scoped under one wrapper and dropped straight into a themed page.
PREVIEW_CLASS = "doc-preview"

JSON_BLOCK = re.compile(r"```json\n(.*?)\n```", re.S)
_RULE = re.compile(r"([^{}]+)\{([^}]*)\}", re.S)


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
    pages = _mirror_reference()
    _check_nav(families)
    print(f"Готово: галерея ({len(families)}), справочники ({len(pages)}), примеры")


def _check_nav(families: list[str]) -> None:
    """A new illustration must reach the menu, not just the disk.

    `zensical build --strict` warns about an orphan page, but only after the
    site is generated; failing here points at the file to edit.
    """
    nav = (REPO / "zensical.toml").read_text(encoding="utf-8")
    missing = [tag for tag in families if f'"gallery/{tag}.md"' not in nav]
    if missing:
        raise SystemExit(
            "страницы галереи не перечислены в nav (zensical.toml): "
            + ", ".join(f"gallery/{tag}.md" for tag in missing)
        )


# --- downloads and the full example ------------------------------------


def _copy_download(archive: Path) -> None:
    """The zip a teacher installs, served from the site itself."""
    shutil.copy2(archive, DOCS / "assets" / archive.name)


def _write_example() -> None:
    """The worked example as the real artefact, not a description of one."""
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


# --- gallery ------------------------------------------------------------


def _write_gallery() -> list[str]:
    pages = []
    for entry in load_visuals().values():
        parts = [entry.doc("card.md").read_text(encoding="utf-8").rstrip(), ""]
        for spec_path in entry.specs:
            raw = json.loads(spec_path.read_text(encoding="utf-8"))
            model = parse_visual(raw, spec_path.name)
            name = f"{entry.tag}-{spec_path.stem}.svg"
            (DOCS / "assets" / name).write_text(
                build_svg(model, scope=spec_path.stem, standalone=True), encoding="utf-8"
            )
            parts.append(
                f"### {spec_path.stem}\n\n"
                f"![{spec_path.stem}](../assets/{name})\n\n"
                f'??? note "Как это записано"\n\n'
                f"    ```json\n{_indent(raw)}\n    ```\n"
            )
        (DOCS / "gallery" / f"{entry.tag}.md").write_text("\n".join(parts), encoding="utf-8")
        pages.append(entry.tag)
        print(f"  gallery/{entry.tag}.md ({len(entry.specs)} шт.)")
    return pages


def _indent(raw: object) -> str:
    text = json.dumps(raw, ensure_ascii=False, indent=2)
    return "\n".join("        " + line for line in text.splitlines())


# --- task kinds ---------------------------------------------------------


def _write_questions() -> None:
    """One page with every task kind, each shown as it will be printed."""
    parts = [
        "# Виды заданий\n",
        "Девять видов, из которых собираются задания. Ниже — как каждый "
        "выглядит на листе и что сказать Claude, чтобы получить такой.\n",
        "Правильные ответы в теле задания не печатаются никогда: рендерер "
        "собирает их в раздел «Ответы» в конце документа, а раздаточный "
        "вариант печатается вообще без него.\n",
        f"<style>{_scoped_css()}</style>\n",
    ]
    for entry in load_questions().values():
        card = entry.card.read_text(encoding="utf-8").strip()
        parts.append(re.sub(r"^# ", "## ", card, flags=re.M))
        parts.append("")
        parts.append(_preview(entry))
        parts.append("")
    (DOCS / "questions.md").write_text("\n".join(parts), encoding="utf-8")
    print(f"  questions.md ({len(load_questions())} видов)")


def _preview(entry: QuestionType) -> str:
    """Render the kind's documented example through the real renderer.

    The same JSON the reference shows and the tests exercise, so a picture on
    this page cannot show something the skill would not produce.
    """
    match = JSON_BLOCK.search(entry.doc.read_text(encoding="utf-8"))
    if match is None:
        raise SystemExit(f"в {entry.doc} нет примера в блоке ```json")
    task = {
        "type": "task",
        "blocks": [
            {"type": "text", "body": _STATEMENTS[entry.tag]},
            json.loads(match.group(1)),
        ],
    }
    html = build_document(parse_document({}), [parse_block(task, entry.tag)])
    body = html.split("<body>\n", 1)[1].split("\n</body>", 1)[0]
    return f'<div class="{PREVIEW_CLASS}" markdown="0">\n{body}\n</div>'


_STATEMENTS = {
    "open": "Автомобиль движется равномерно со скоростью υ = 72 км/ч. Какой путь он пройдёт за 15 минут?",
    "choice": "Как меняется скорость при равноускоренном движении?",
    "match": "Сопоставьте величины и единицы их измерения.",
    "fill_text": "Вставьте пропущенные слова.",
    "fill_table": "Заполните пропуски в таблице.",
    "plot": "Постройте график скорости от времени.",
    "true_false": "Отметьте, верны ли утверждения.",
    "rank": "Расставьте события в правильном порядке.",
    "classify": "Распределите величины по группам.",
}


def _scoped_css() -> str:
    """The document stylesheet, confined to one wrapper.

    Everything the renderer emits is class-based, so prefixing each selector
    is enough; the page-level rules become rules of the wrapper.
    """
    scoped = []
    for match in _RULE.finditer(BASE_CSS):
        selectors = [s.strip() for s in match.group(1).split(",") if s.strip()]
        body = match.group(2).strip()
        rewritten = []
        for selector in selectors:
            if selector.startswith(("/*", "@")):
                continue
            selector = re.sub(r"/\*.*?\*/", "", selector, flags=re.S).strip()
            if not selector:
                continue
            if selector in (":root", "*", "html", "body"):
                rewritten.append(f".{PREVIEW_CLASS}" if selector in ("body", ":root") else
                                 f".{PREVIEW_CLASS} *")
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
