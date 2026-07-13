#!/usr/bin/env python3
"""Собирает распространяемый zip-бандл скилла для Settings → Skills.

Состав бандла определяется структурой репозитория, а не списком в этом
скрипте: в архив уходит **вся** папка `worksheet-builder/` (она и есть
бандл — dev-обвязка живёт в корне репо), минус генерируемый мусор
(__pycache__, output/ рендеров примеров, *.preview.html, *.pyc).

Дополнительно скрипт сверяет SKILL.md с содержимым архива: каждый путь
вида `references/...`, `scripts/...`, `examples/...`, `worksheet_builder/...`,
упомянутый в SKILL.md, обязан существовать в бандле — рассинхрон
(«SKILL.md обещает файл, которого нет у пользователя») роняет сборку.

Корень архива — папка `worksheet-builder/` со SKILL.md внутри, то есть zip
готов к загрузке в Settings → Capabilities → Skills как есть.

Запуск (из корня репо):
    python build_bundle.py
    python build_bundle.py --out dist/skill.zip
"""
import argparse
import re
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILL_DIR = REPO_ROOT / "worksheet-builder"
BUNDLE_ROOT = "worksheet-builder"  # имя папки-корня внутри архива

# Генерируемый мусор: сегменты пути и суффиксы, которые в бандл не идут.
# Скрытые папки (.venv, кэши инструментов) и *.egg-info могут появляться
# внутри папки скилла как побочный эффект локального dev — тоже мусор.
JUNK_DIRS = {"__pycache__", "output"}
JUNK_SUFFIXES = (".pyc", ".preview.html")


def _is_junk_part(part: str) -> bool:
    return part in JUNK_DIRS or part.startswith(".") or part.endswith(".egg-info")

# Пути этих видов, упомянутые в SKILL.md, обязаны существовать в бандле.
SKILL_MD_PATH_RE = re.compile(
    r"\b((?:references|scripts|examples|worksheet_builder)/[\w./-]+\w)"
)


def _is_junk(rel: Path) -> bool:
    return any(_is_junk_part(p) for p in rel.parts) or rel.name.endswith(JUNK_SUFFIXES)


def _iter_files() -> list[Path]:
    if not (SKILL_DIR / "SKILL.md").is_file():
        raise SystemExit(f"Не найден {SKILL_DIR / 'SKILL.md'} — запускай из корня репо")
    return sorted(
        p for p in SKILL_DIR.rglob("*")
        if p.is_file() and not _is_junk(p.relative_to(SKILL_DIR))
    )


def _check_skill_md_paths(bundled: set[str]) -> None:
    """SKILL.md не должен ссылаться на файлы, которых в бандле нет."""
    text = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    mentioned = set(SKILL_MD_PATH_RE.findall(text))
    bundled_dirs = {str(Path(f).parent.as_posix()) for f in bundled}
    missing = [
        m for m in mentioned
        if m not in bundled and m.rstrip("/") not in bundled_dirs
    ]
    if missing:
        raise SystemExit(
            "SKILL.md упоминает пути, которых нет в бандле:\n  "
            + "\n  ".join(sorted(missing))
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist/worksheet-builder-skill.zip",
                        help="Путь к выходному zip (по умолчанию dist/worksheet-builder-skill.zip)")
    args = parser.parse_args()

    files = _iter_files()
    rel_paths = {p.relative_to(SKILL_DIR).as_posix() for p in files}
    _check_skill_md_paths(rel_paths)

    out = (REPO_ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(SKILL_DIR)
            zf.write(path, f"{BUNDLE_ROOT}/{rel.as_posix()}")

    size_kb = out.stat().st_size / 1024
    print(f"Собрано {len(files)} файлов -> {out} ({size_kb:.0f} КБ)")


if __name__ == "__main__":
    main()
