#!/usr/bin/env python3
"""Генерирует страницы сайта документации из уже существующих источников.

Правило сайта то же, что и правило скилла: **ничего не переписывать руками
второй раз**. Копия документации расходится с кодом (так уже случилось с
README), поэтому всё, что дублирует существующий источник, сюда
генерируется:

* **галерея SVG** — из спек `gallery/<семейство>/*.json` тем же кодом, что
  рисует иллюстрации в документах (`parse_visual` + `build_standalone_svg`,
  ровно как `--visual`). Спека невалидна — сборка падает; картинка на сайте
  физически не может отличаться от той, что получит учитель;
* **справочники скилла** — зеркало `worksheet-builder/references/**.md`
  (дерево сохраняется, поэтому относительные ссылки внутри них остаются
  рабочими).

Рукописные страницы (`docs/index.md`, `docs/quickstart.md`, вступления
к страницам галереи `gallery/<семейство>.md`) скрипт не трогает.

Всё сгенерированное складывается в `docs/gallery/` и `docs/reference/` —
эти папки в .gitignore: источник в репозитории один.

Запуск (из корня репо):
    python build_docs.py          # затем: zensical serve
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "worksheet-builder"))

from worksheet_builder.models import parse_visual  # noqa: E402
from worksheet_builder.standalone import build_standalone_svg  # noqa: E402

GALLERY_SRC = REPO_ROOT / "gallery"
REFERENCES_SRC = REPO_ROOT / "worksheet-builder" / "references"
DOCS = REPO_ROOT / "docs"
GALLERY_OUT = DOCS / "gallery"
REFERENCE_OUT = DOCS / "reference"

GENERATED_NOTE = (
    "!!! info \"Страница собрана автоматически\"\n\n"
    "    Источник — {source}. Правки вносятся туда, "
    "страница пересобирается `python build_docs.py`.\n"
)


def _reset(directory: Path) -> None:
    """Полностью пересобираем: удалённая спека не должна пережить сборку."""
    if directory.exists():
        shutil.rmtree(directory)
    directory.mkdir(parents=True)


def _gallery_item(spec_path: Path, assets: Path, family: str) -> str:
    """Один экспонат галереи: заголовок, отрисованный SVG, свёрнутая спека."""
    raw = json.loads(spec_path.read_text(encoding="utf-8"))
    # Та же точка входа, что у `--visual`: невалидная спека роняет сборку
    # сайта с тем же сообщением, что увидел бы автор документа.
    model = parse_visual(raw, spec_path.name)
    svg_name = f"{family}-{spec_path.stem}.svg"
    (assets / svg_name).write_text(build_standalone_svg(model), encoding="utf-8")

    spec_json = json.dumps(raw, ensure_ascii=False, indent=2)
    indented = "\n".join("        " + line for line in spec_json.splitlines())
    return (
        f"### {spec_path.stem}\n\n"
        f"![{spec_path.stem}](assets/{svg_name})\n\n"
        f'??? note "Спека `{spec_path.name}`"\n\n'
        f"    ```json\n{indented}\n    ```\n"
    )


def build_gallery() -> list[str]:
    """Страница на семейство визуалов: вступление (рукописное) + экспонаты."""
    _reset(GALLERY_OUT)
    assets = GALLERY_OUT / "assets"
    assets.mkdir()
    pages = []
    families = sorted(p for p in GALLERY_SRC.iterdir() if p.is_dir())
    for family_dir in families:
        family = family_dir.name
        specs = sorted(family_dir.glob("*.json"))
        if not specs:
            continue
        intro_path = GALLERY_SRC / f"{family}.md"
        if not intro_path.exists():
            raise SystemExit(
                f"Нет вступления {intro_path.relative_to(REPO_ROOT)} "
                f"для семейства {family!r}"
            )
        parts = [intro_path.read_text(encoding="utf-8").rstrip(), ""]
        parts += [_gallery_item(spec, assets, family) for spec in specs]
        (GALLERY_OUT / f"{family}.md").write_text("\n".join(parts), encoding="utf-8")
        pages.append(f"gallery/{family}.md")
        print(f"  gallery/{family}.md ({len(specs)} шт.)")
    return pages


def _mirror_reference(src: Path, dst: Path) -> None:
    """Копия справочника с пометкой о происхождении после заголовка H1."""
    text = src.read_text(encoding="utf-8")
    note = GENERATED_NOTE.format(source=f"`{src.relative_to(REPO_ROOT).as_posix()}`")
    lines = text.splitlines()
    # Пометка идёт после H1: заголовок страницы Zensical берёт из первого
    # заголовка, а перед ним ему нужен именно он, а не блок-врезка.
    if lines and lines[0].startswith("# "):
        body = "\n".join([lines[0], "", note, *lines[1:]])
    else:
        body = note + "\n" + text
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(body + "\n", encoding="utf-8")


def build_reference() -> list[str]:
    """Зеркало справочников скилла — с сохранением дерева (ссылки внутри)."""
    _reset(REFERENCE_OUT)
    pages = []
    for src in sorted(REFERENCES_SRC.rglob("*.md")):
        rel = src.relative_to(REFERENCES_SRC)
        _mirror_reference(src, REFERENCE_OUT / rel)
        pages.append(f"reference/{rel.as_posix()}")
        print(f"  reference/{rel.as_posix()}")
    return pages


def main() -> None:
    if not GALLERY_SRC.is_dir():
        raise SystemExit(f"Не найдена {GALLERY_SRC} — запускай из корня репо")
    print("Галерея:")
    gallery = build_gallery()
    print("Справочники:")
    reference = build_reference()
    print(f"Готово: {len(gallery) + len(reference)} страниц в docs/")


if __name__ == "__main__":
    main()
