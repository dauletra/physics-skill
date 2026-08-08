"""The generated site — the part of it a browser can silently ignore.

The showcase promises that every sheet on it is the renderer's own output, so
the document stylesheet is scoped and pasted into a themed page. A selector
that comes out malformed costs nothing visible at build time: the browser
drops the rule and the preview quietly stops matching the printed sheet.
That is what these tests are for.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))

import build_site  # noqa: E402
from physics_svg.document.assets import BASE_CSS  # noqa: E402
from physics_svg.presentation import build_data, build_page  # noqa: E402
from physics_svg.presentation import load_workspace as load_lesson  # noqa: E402
from physics_svg.presentation.slides import load_all as load_slides  # noqa: E402
from physics_svg.visuals import load_all as load_visuals  # noqa: E402

RULE = re.compile(r"([^{}]+)\{([^}]*)\}", re.S)


def rules() -> list[tuple[str, str]]:
    scoped = build_site._scoped_css()
    return [(m.group(1).strip(), m.group(2).strip()) for m in RULE.finditer(scoped)]


class TestGalleryCards:
    """A card that arranges its own pictures has to arrange all of them.

    Otherwise the page silently splits in two: a tour through cases, and a
    tail of unexplained examples that the author never noticed appearing.
    """

    def test_placed_specs_exist_and_cover_the_type(self) -> None:
        for entry in load_visuals().values():
            card = entry.doc("card.md").read_text(encoding="utf-8")
            placed = [match.group(1).strip() for match in build_site.SPEC_FENCE.finditer(card)]
            if not placed:
                continue  # a plain card: the page lists the specs itself
            assert sorted(placed) == sorted(path.stem for path in entry.specs), (
                f"{entry.tag}/card.md расставляет {sorted(placed)}, "
                f"а спеки — {sorted(path.stem for path in entry.specs)}"
            )


class TestSlidesPage:
    """The one page the site does not render for itself.

    Everything else in the showcase is produced by the renderer a teacher's
    files go through; a slide is drawn by the player, in a browser. So the
    page embeds the player itself — one built presentation per template —
    and its job is to carry every card, every template and the whole example.
    """

    def test_every_template_is_shown_by_the_player(self) -> None:
        page = build_site._slides_page()
        for entry in load_slides().values():
            for template in entry.templates:
                name = f"slide-{entry.tag}-{template.slug}.html"
                assert name in page, f"заготовка '{entry.tag}/{template.slug}' не попала на страницу"
                asset = build_site.DOCS / "assets" / name
                # A real built page, not a picture of one: the blob is what
                # proves the player draws this preview at runtime.
                assert 'id="presentation-data"' in asset.read_text(encoding="utf-8")

    def test_every_kind_reaches_the_page(self) -> None:
        page = build_site._slides_page()
        for entry in load_slides().values():
            heading = entry.card.read_text(encoding="utf-8").splitlines()[0].lstrip("# ")
            assert f"## {heading}" in page, f"карточка вида '{entry.tag}' не попала на страницу"

    def test_it_opens_a_presentation_that_builds(self) -> None:
        assert "assets/example-presentation.html" in build_site._slides_page()
        # The link is only worth anything if the lesson behind it still builds.
        lesson = load_lesson(build_site.EXAMPLE)
        page = build_page(build_data(lesson.presentation, lesson.slides))
        assert 'id="presentation-data"' in page


class TestScopedStylesheet:
    def test_no_comment_survives_into_a_selector(self) -> None:
        # A comment left in a selector list makes the whole list invalid.
        for selectors, _body in rules():
            assert "/*" not in selectors and "*/" not in selectors, selectors

    def test_every_selector_is_confined_to_the_wrapper(self) -> None:
        for selectors, _body in rules():
            for selector in selectors.split(","):
                assert selector.strip().startswith(f".{build_site.PREVIEW_CLASS}"), selector

    def test_nothing_is_lost_on_the_way(self) -> None:
        """Every rule of the stylesheet reaches the page.

        Counted rather than compared: the transformation is the point of the
        function, but a rule silently disappearing is the bug it had.
        """
        source = re.sub(r"/\*.*?\*/", "", BASE_CSS, flags=re.S)
        expected = [m for m in RULE.finditer(source) if m.group(2).strip()]
        # Plus the one rule the site appends to frame the sheet.
        assert len(rules()) == len(expected) + 1

    def test_the_page_level_rules_become_the_wrapper(self) -> None:
        """`body`/`html`/`:root` describe the sheet, not everything on it."""
        wrapper = f".{build_site.PREVIEW_CLASS}"
        for selectors, body in rules():
            if "--font-main" in body:  # the `:root` rule
                assert selectors == wrapper
