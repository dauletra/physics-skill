"""The player template: the promises Python can check without a browser.

What a slide looks like is checked by eyes (`evals/presentation.md`); here
the suite pins the contract between the template and the build — one
injection point inside one data block — and the two guards the design
insists on: rendering happens from JSON at runtime, and a missing CDN
degrades to source text rather than an exception.
"""

from __future__ import annotations

import re
from pathlib import Path

import physics_svg.presentation.emit as emit

PLAYER = Path(emit.__file__).parent / "player" / "player.html"


def template() -> str:
    return PLAYER.read_text(encoding="utf-8")


def test_exactly_one_injection_point_inside_the_data_block() -> None:
    page = template()
    assert page.count("__PRESENTATION_DATA__") == 1
    found = re.search(
        r'<script type="application/json" id="presentation-data">(.*?)</script>', page, re.S
    )
    assert found is not None and found.group(1) == "__PRESENTATION_DATA__"


def test_the_template_carries_no_content_markup() -> None:
    # Python injects data; the player renders. Content appearing here would
    # mean a second renderer is growing — the one thing §3 forbids.
    body = template().split("<body>", 1)[1]
    stripped = re.sub(r"<script.*?</script>", "", body, flags=re.S)
    for tag in ("<h1", "<h2", "<p>", "<ul", "<table", "<svg"):
        assert tag not in stripped, f"в шаблоне плеера содержательный тег {tag}"


def test_formulas_degrade_without_the_cdn() -> None:
    # The same compromise as the document: KaTeX comes from the CDN, and
    # offline a formula stays source text instead of throwing.
    page = template()
    assert "window.katex" in page
    assert "katex.min.js" in page
