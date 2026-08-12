#!/usr/bin/env python3
"""Entry point of the skill bundle.

    python <путь-к-скиллу>/scripts/render.py build <папка-черновика>
    python <путь-к-скиллу>/scripts/render.py visual <спека.json>

Nothing is installed and nothing is downloaded: the package ships inside the
bundle and depends only on the standard library. Earlier versions had to
fetch a validation library on first use, which meant network access, a wait,
and a way to fail before drawing anything.

The package ships as `physics_svg.zip` and is imported from there — the
uploader counts files, so a hundred and one modules travel as one. Only the
archive goes on the path: a second entry would let an unpacked copy lying
beside it win over the one that was built.
"""

import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent
PACKAGE = BUNDLE / "physics_svg.zip"

if not PACKAGE.exists():  # pragma: no cover - guard for a half-unpacked archive
    sys.exit(
        f"рядом со скриптом нет {PACKAGE.name} — похоже, архив скилла распакован "
        "не полностью. Распакуйте его целиком и запустите снова."
    )

sys.path.insert(0, str(PACKAGE))

if sys.version_info < (3, 10):  # pragma: no cover - guard for old sandboxes
    sys.exit(
        f"Нужен Python 3.10 или новее, а запущен {sys.version.split()[0]}. "
        "Сообщите об этом учителю — скилл собран под более новую версию."
    )

from physics_svg.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
