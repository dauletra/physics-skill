#!/usr/bin/env python3
"""Entry point of the skill bundle.

    python <путь-к-скиллу>/scripts/render.py build <папка-черновика>
    python <путь-к-скиллу>/scripts/render.py visual <спека.json>

Nothing is installed and nothing is downloaded: the package ships inside the
bundle and depends only on the standard library. Earlier versions had to
fetch a validation library on first use, which meant network access, a wait,
and a way to fail before drawing anything.
"""

import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BUNDLE))

if sys.version_info < (3, 10):  # pragma: no cover - guard for old sandboxes
    sys.exit(
        f"Нужен Python 3.10 или новее, а запущен {sys.version.split()[0]}. "
        "Сообщите об этом учителю — скилл собран под более новую версию."
    )

from physics_svg.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
