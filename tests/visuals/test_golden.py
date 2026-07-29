"""Frozen SVG output for every example spec.

Goldens catch the change nobody meant to make: a shared element nudged by
half a unit shows up as five files differing at once. They are not a design
review — when a picture changes on purpose, regenerate and *look* at the
diff, and at the contact sheet.

    REGEN_GOLDEN=1 python -m pytest tests/visuals -q
"""

from __future__ import annotations

import os
from pathlib import Path

from physics_svg.visuals import build_svg

GOLDEN_DIR = Path(__file__).resolve().parent.parent / "golden" / "visuals"
REGENERATE = os.environ.get("REGEN_GOLDEN") == "1"


def test_matches_golden(example) -> None:
    # A fixed scope keeps element ids stable across runs.
    actual = build_svg(example.model, scope="v", standalone=True)
    path = GOLDEN_DIR / f"{example.type.tag}-{example.path.stem}.svg"
    if REGENERATE or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(actual, encoding="utf-8")
        if not REGENERATE:
            return
    assert actual == path.read_text(encoding="utf-8"), (
        f"{example.name}: рендер разошёлся с эталоном {path.name}; "
        "если изменение намеренное — REGEN_GOLDEN=1 и просмотри диф глазами"
    )


def test_golden_directory_has_no_orphans() -> None:
    """A spec that was deleted must not leave its golden behind."""
    from conftest import EXAMPLES

    expected = {f"{e.type.tag}-{e.path.stem}.svg" for e in EXAMPLES}
    actual = {p.name for p in GOLDEN_DIR.glob("*.svg")}
    assert actual - expected == set(), f"эталоны без спеки: {sorted(actual - expected)}"
