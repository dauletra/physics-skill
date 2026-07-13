"""Точка входа рендерера для облачного sandbox (Settings -> Skills).

В отличие от локального контракта (`uv run --project <skill> render-worksheet`),
в контейнере code-execution нет ни uv, ни установленного пакета. Этот скрипт:

  1. при первом запуске в сессии доустанавливает pydantic, если его нет
     (идемпотентно — повторные рендеры внутри сессии мгновенные);
  2. кладёт корень скилла в sys.path и передаёт управление тому же
     `worksheet_builder.cli.main()`, что и локальные обёртки.

Запуск (argv проходит насквозь в CLI):

    python scripts/render.py <workspace>
    python scripts/render.py <workspace> --task task-03
    python scripts/render.py <workspace> --task task-03 --mode student

Требует сетевого доступа контейнера к PyPI (см. SANDBOX-MIGRATION.md,
ограничение №2). Если сети нет — печатает внятную ошибку без traceback.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

# pydantic пинуется диапазоном: гарантированно v2 (на нём написаны модели),
# защита от гипотетического ломающего v3. На HTML-вывод версия не влияет —
# pydantic только валидирует, поэтому golden-тесты остаются стабильными.
_PYDANTIC_SPEC = "pydantic>=2,<3"


def _ensure_pydantic() -> None:
    """Ставит pydantic только если он отсутствует. Идемпотентно: один раз на
    жизнь контейнера, не на каждый вызов."""
    if importlib.util.find_spec("pydantic") is not None:
        return
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "-q",
             "--disable-pip-version-check", _PYDANTIC_SPEC]
        )
    except (subprocess.CalledProcessError, OSError) as e:
        sys.exit(
            f"Не удалось установить {_PYDANTIC_SPEC}: {e}\n"
            "Рендереру нужен pydantic, а контейнеру — доступ к PyPI. "
            "Если сети нет, установка невозможна (см. SANDBOX-MIGRATION.md)."
        )


def main() -> None:
    _ensure_pydantic()
    # Корень скилла (папка с worksheet_builder/) — на два уровня выше:
    # <skill>/scripts/render.py -> <skill>.
    skill_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(skill_root))
    from worksheet_builder.cli import main as cli_main
    cli_main()


if __name__ == "__main__":
    main()
