#!/usr/bin/env python3
"""Собирает распространяемый zip-бандл скилла для Settings → Skills.

Кладёт в архив только то, что нужно в рантайме облачного sandbox: SKILL.md,
пакет рендерера, references, scripts/render.py и examples (как few-shot).
Исключает dev-обвязку (tests, .venv, кэши, uv.lock, pyproject, egg-info) и
любые сгенерированные артефакты в примерах (output/, *.preview.html).

Корень архива — папка `worksheet-builder/` со SKILL.md внутри, то есть zip
готов к загрузке в Settings → Capabilities → Skills как есть.

Запуск (из корня репо):
    python build_bundle.py
    python build_bundle.py --out dist/skill.zip

См. SANDBOX-MIGRATION.md — состав бандла и зачем он такой.
"""
import argparse
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILL_DIR = REPO_ROOT / "worksheet-builder"
BUNDLE_ROOT = "worksheet-builder"  # имя папки-корня внутри архива

# Что кладём (пути относительно worksheet-builder/). Только это и попадёт в zip.
INCLUDE = ["SKILL.md", "worksheet_builder", "references", "scripts", "examples"]

# Имена сегментов пути, при встрече которых файл/папка отбрасывается целиком.
EXCLUDE_PARTS = {
    ".venv", "tests", "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "output",  # сгенерированный рендер внутри examples/*/
}


def _excluded(rel: Path) -> bool:
    parts = set(rel.parts)
    if parts & EXCLUDE_PARTS:
        return True
    if any(p.endswith(".egg-info") for p in rel.parts):
        return True
    if rel.suffix == ".pyc" or rel.name.endswith(".preview.html"):
        return True
    return False


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for entry in INCLUDE:
        src = SKILL_DIR / entry
        if not src.exists():
            raise SystemExit(f"Ожидался {src}, но его нет — состав бандла разошёлся с репо")
        if src.is_file():
            files.append(src)
        else:
            files.extend(p for p in src.rglob("*") if p.is_file())
    # Отфильтровать исключения и отсортировать для детерминированного архива.
    kept = [p for p in files if not _excluded(p.relative_to(SKILL_DIR))]
    return sorted(kept)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="dist/worksheet-builder-skill.zip",
                        help="Путь к выходному zip (по умолчанию dist/worksheet-builder-skill.zip)")
    args = parser.parse_args()

    out = (REPO_ROOT / args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    files = _iter_files()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in files:
            rel = path.relative_to(SKILL_DIR)
            zf.write(path, f"{BUNDLE_ROOT}/{rel.as_posix()}")

    size_kb = out.stat().st_size / 1024
    print(f"Собрано {len(files)} файлов -> {out} ({size_kb:.0f} КБ)")


if __name__ == "__main__":
    main()
